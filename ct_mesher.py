import ants
import meshio
import vtk
from pymeshfix import _meshfix
import gmsh
import pygmsh
import pymeshlab as pmsh
from vtk.util import numpy_support
import numpy as np
import netgen as libngpy
import pyvista as pv
import pyacvd


def tetrahedral_mesher_bad(stl_file_name, mesh_file_name, detail_level, size_range):
    geom = libngpy._stl.STLGeometry(stl_file_name)
    mesh_netgen = geom.GenerateMesh()
    cells = np.asarray([list(map(lambda x: x.nr, els.vertices)) for els in mesh_netgen.Elements3D()], dtype=np.int32)

    points = np.asarray([list(point) for point in mesh_netgen.Points()], dtype=np.float64)
    points = mesh_netgen.Coordinates()
    mesh = meshio.Mesh(points=points, cells=[("tetra", cells)]) # only tets
    mesh.write(mesh_file_name)


def vtk2stl(image, iter_num=50, relax=0.1, dec=0.0):
    '''
    Compute stl mesh from image vtk
    '''

    dmc = vtk.vtkDiscreteMarchingCubes()
    dmc.SetInputData(image)
    dmc.GenerateValues(1, 1, 1)
    dmc.Update()
    deci = vtk.vtkDecimatePro()
    deci.SetInputConnection(dmc.GetOutputPort())
    deci.SetTargetReduction(dec)
    deci.Update()
    smooth_filter = vtk.vtkSmoothPolyDataFilter()
    smooth_filter.SetInputConnection(deci.GetOutputPort())
    smooth_filter.SetNumberOfIterations(iter_num)
    smooth_filter.SetRelaxationFactor(relax)
    smooth_filter.FeatureEdgeSmoothingOff()
    smooth_filter.BoundarySmoothingOn()
    smooth_filter.Update()
    return smooth_filter


def tovtk_image(img, spacing, origin, vtktype=vtk.VTK_CHAR):
    '''
    A function to convert numpy array to vtk image
    '''

    # swap due to vtk axis definitions
    img = img.swapaxes(0, 2)
    vtkdata = numpy_support.numpy_to_vtk(
        img.ravel(), deep=True, array_type=vtktype)
    image_data = vtk.vtkImageData()

    n_x, n_y, n_z = img.shape
    image_data.SetDimensions(n_z, n_y, n_x)
    image_data.SetSpacing((spacing[0], spacing[1], spacing[2]))
    image_data.SetOrigin((origin[0], origin[1], origin[2]))

    image_data.GetPointData().SetScalars(vtkdata)

    return image_data


def stl_from_ct(image, lower_int, iter_num,
                relax, detail_level, stl_file_name, method='meshlab', ratio=10):
    stlWriter = vtk.vtkSTLWriter()
    masked_image = ants.get_mask(
        image, image.numpy().min() + lower_int, None, 0)
    moving_vtk = tovtk_image(masked_image.numpy(), spacing=masked_image.spacing,
                             origin=masked_image.origin)
    moving_stl = vtk2stl(moving_vtk, iter_num, relax)
    stlWriter.SetFileName(stl_file_name)
    stlWriter.SetInputConnection(moving_stl.GetOutputPort())
    stlWriter.Write()
    _meshfix.clean_from_file(stl_file_name, stl_file_name)
    if method=='meshlab':
        ms = pmsh.MeshSet()
        ms.load_new_mesh(stl_file_name)
        ms.meshing_merge_close_vertices()

        ms.meshing_isotropic_explicit_remeshing(iterations=iter_num,
                                                targetlen=pmsh.Percentage(detail_level))
        ms.save_current_mesh(stl_file_name)
    elif method=='ACVD':
        mesh = pv.read(stl_file_name)
        print('')
        clus = pyacvd.Clustering(mesh)
        #clus.subdivide(3)
        clus.cluster(int(len(mesh.points)/ratio))
        remesh = clus.create_mesh()
        remesh.save(stl_file_name)

def only_ACVD(stl_file_name, ratio):
        mesh = pv.read(stl_file_name)
        clus = pyacvd.Clustering(mesh)
        #clus.subdivide(3)
        clus.cluster(int(len(mesh.points)/ratio))
        remesh = clus.create_mesh()
        remesh.save(stl_file_name)
    

def tetrahedral_mesher(stl_file_name, mesh_file_name, detail_level, size_range):
    gmsh.initialize()
    with pygmsh.geo.Geometry() as geom:
        gmsh.option.setNumber("General.Terminal", 1)

        gmsh.option.setNumber("Mesh.CharacteristicLengthMin",
                              detail_level * (1. - size_range / 200.))
        gmsh.option.setNumber("Mesh.CharacteristicLengthMax",
                              detail_level * (1. + size_range / 200.))
        gmsh.option.setNumber("Mesh.Optimize", 1)
        gmsh.option.setNumber("Mesh.QualityType", 2)
        gmsh.option.setNumber("Mesh.OptimizeNetgen", 1)
        gmsh.merge(stl_file_name)
        n = gmsh.model.getDimension()
        s = gmsh.model.getEntities(n)
        l = gmsh.model.geo.addSurfaceLoop([s[i][1] for i in range(len(s))])
        gmsh.model.geo.addVolume([l])
        mesh = geom.generate_mesh(dim=3, verbose=False, algorithm=8)
        mesh = meshio.Mesh(points=mesh.points, cells=[("tetra", mesh.cells_dict['tetra'])]) # only tets
        mesh.write(mesh_file_name)
        return mesh

if __name__ == '__main__':
    pass
