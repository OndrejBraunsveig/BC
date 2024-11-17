import vtk
import numpy as np
import math
from tqdm import trange
import ants
from scipy.ndimage import distance_transform_edt
import os

def STL2Mask(stl_filename, res=1., pad=75, edt=True):

    mesh_file_name = f'{stl_filename}.stl'
    image_file_name = f'{stl_filename}.mha'

    reader = vtk.vtkSTLReader()
    pol2stenc = vtk.vtkPolyDataToImageStencil()
    imgstenc = vtk.vtkImageStencil()

    reader.SetFileName(mesh_file_name)
    reader.Update()

    ref_mesh = reader.GetOutput()
    ref_volume = vtk.vtkImageData()
        
    # define output volume dimension
    spacing = np.array([res, res, res])

    ref_volume.SetSpacing(spacing)

    bounds = np.asarray(ref_mesh.GetBounds())
    print(f'Bounds: {bounds}')

    dim = [math.ceil((bounds[ii*2+1] - bounds[ii*2]) / spacing[ii]) for ii in range(0,3)]
    origin = [bounds[ii*2] + spacing[ii] / 2 for ii in range(0,3)]
    extent = (0,dim[0] - 1,0,dim[1] -1 ,0,dim[2]-1)

    ref_volume.SetOrigin(origin)
    ref_volume.SetDimensions(dim)
    ref_volume.SetExtent(extent)

    ref_volume.AllocateScalars(vtk.VTK_DOUBLE, 1)

    #Fill the image with white voxels
    for i in trange(0,ref_volume.GetNumberOfPoints()):
        ref_volume.GetPointData().GetScalars().SetTuple1(i,1)

    pol2stenc.SetInputData(ref_mesh)

    pol2stenc.SetOutputOrigin(origin)
    pol2stenc.SetOutputSpacing(spacing)
    pol2stenc.SetOutputWholeExtent(ref_volume.GetExtent())

    pol2stenc.Update()

    imgstenc.SetInputData(ref_volume)
    imgstenc.SetInputConnection(2, pol2stenc.GetOutputPort())

    bcd_val = 0 
    imgstenc.ReverseStencilOff()
    imgstenc.SetBackgroundValue(bcd_val)
    imgstenc.Update()
    tmp = imgstenc.GetOutput()

    writer = vtk.vtkMetaImageWriter()
    writer.SetFileName(image_file_name)
    writer.SetInputData(tmp)
    writer.Write()

    image = ants.image_read(image_file_name)
    if edt:
        edt = distance_transform_edt(image.numpy(), image.spacing)
        image = ants.from_numpy(edt, image.origin, 
                                    image.spacing, image.direction)
        
    image = ants.pad_image(image, pad_width=(pad, pad, pad), value=bcd_val)
    ants.image_write(image, image_file_name)
