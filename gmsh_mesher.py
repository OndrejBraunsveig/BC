import ants
import vtk
from pymeshfix import _meshfix
from meshing_utils import tovtk_image, vtk2stl
import gmsh
import pygmsh
import os



def stl_from_ct(image, lower_int, iter_num,
                relax, detail_level, stl_file_name):
    stlWriter = vtk.vtkSTLWriter()
    masked_image = ants.get_mask(
        image, image.numpy().min() + lower_int, None, 0)
    moving_vtk = tovtk_image(masked_image.numpy(), spacing=masked_image.spacing,
                             origin=masked_image.origin)
    moving_stl = vtk2stl(moving_vtk, iter_num, relax)
    stlWriter.SetFileName(stl_file_name)
    stlWriter.SetInputConnection(moving_stl.GetOutputPort())
    stlWriter.Write()
    moving_stl = vtk2stl(moving_vtk, iter_num, relax)
    stlWriter.SetFileName(stl_file_name)
    stlWriter.SetInputConnection(moving_stl.GetOutputPort())
    stlWriter.Write()
    _meshfix.clean_from_file(stl_file_name, stl_file_name)


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
        #mesh.prune_z_0()
        #mesh.remove_lower_dimensional_cells()
        mesh.write(mesh_file_name)


if __name__ == '__main__':
    pass
