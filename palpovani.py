import numpy as np
import pandas as pd
import ants
import os
import glob
import re
from tqdm import trange
from .ct_mesher import stl_from_ct, only_ACVD
import pyvista as pv
from scipy.spatial import distance_matrix

def compute_mesh(image, stl_file_name):
    
    lower_int = 0.1
    # vtk stl generator
    iter_num = 25
    relax = 0.15
    size_range = 10. #percent
    detail_level = 1.5
    stl_from_ct(image, lower_int, iter_num, relax, detail_level, stl_file_name,
               method='ACVD', ratio=15)
    
    return None

def compute_max_distance(mesh):
    points = mesh.points
    D = distance_matrix(points, points)
    indices = np.where(D == D.max())[0]
    return points[indices[0]],points[indices[1]]


points = pd.read_csv('left_points.csv')

ref_points = pd.DataFrame({'x': points['Points:0'].values,
                       'y': points['Points:1'].values,
                       'z': points['Points:2'].values})


template = ants.image_read("cesta k tepmplate.mha")
compute_mesh(template, 'cesta k template.stl')

for i in trange(len(names)):
    patient = names[i]
    #print(patient)
    ii = re.findall("warped", patient)
    if len(ii)==1:
        
        aff_fwd_file = patient + '.stl.mhaafn_fwd.mat'
        warp_fwd_file = patient + '.stl.mhawarp_fwd.nii.gz'
        points_trns = ants.apply_transforms_to_points(dim=3, points=ref_points,
                                                          transformlist=[warp_fwd_file, 
                                                                         aff_fwd_file], 
                                                          whichtoinvert=[False, False])
        print(patient)
        print(soubory[i])
        points_trns['ID'] = points['vtkOriginalPointIds']
        if os.path.exists(zdroj + soubory[i]):
#            x1, x2 = compute_max_distance(pv.read(zdroj + soubory[i])) tohle ne, tohle děláme v kroku pred tím, tady by to bylo zbytecne
#            new_row = {"x": x1[0], "y": x1[1], 'z': x1[2]}
#            points_trns.loc[15] = new_row
#            new_row = {"x": x2[0], "y": x2[1], 'z': x2[2]}
#            points_trns.loc[16] = new_row
#
            points_trns.to_excel(patient + '.xlsx')
#
#            del x1
#            del x2
        else:
            print(f"Soubor {zdroj +soubory[i]} neexistuje. Přeskakuji.")
