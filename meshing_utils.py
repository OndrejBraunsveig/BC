import vtk
from numpy.linalg import norm
from vtkmodules.util import numpy_support
import logging
import sys


logging.basicConfig(
    level=logging.DEBUG,
    format="[%(levelname)s]: %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stdout)

logging.addLevelName(logging.DEBUG,
                     "\033[94m%s\033[0m" % logging.getLevelName(logging.DEBUG))
logging.addLevelName(logging.INFO,
                     "\033[92m%s\033[0m" % logging.getLevelName(logging.INFO))
logging.addLevelName(logging.WARNING,
                     "\033[93m%s\033[0m" % logging.getLevelName(logging.WARNING))
logging.addLevelName(logging.ERROR,
                     "\033[1;31m%s\033[0m" % logging.getLevelName(logging.ERROR))

logging.disable(logging.DEBUG)

log = logging.getLogger("My Logger")


def vtk2stl(image, iter_num=50, relax=0.1, dec=0):
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



