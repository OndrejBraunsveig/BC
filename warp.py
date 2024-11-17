#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Nov  8 13:37:11 2021

@author: alex
"""
import ants
import logging
import os
#from .gmsh_mesher import stl_from_ct
import pyvista as pv

from tqdm import trange
from scipy.spatial import KDTree
import numpy as np

def warp(project_id):

    filename = f'R_{project_id}'
    model_mha = f'{filename}.mha'
    template_mha = 'T_3.mha'

    # Load the moving and fixed images
    original_image = ants.image_read(model_mha)
    template_file = ants.image_read(template_mha)

    print(ants.get_center_of_mass(original_image))
    print(original_image.min())
    print(original_image.max())
    print(ants.get_center_of_mass(template_file))
    print(template_file.min())
    print(template_file.max())

    aligned_model_mha = f'warped_{model_mha}'
    afn_fwd = f'{filename}_afn_fwd.mat'
    warp_fwd = f'{filename}_warp_fwd.nii.gz'
    afn_inv = f'{filename}_afn_inv.mat'
    warp_inv = f'{filename}_warp_inv.nii.gz'
    overwrite = True # prepsat nebo vyhledat nedodelane?
    mi = original_image
    #int_offset = mi.numpy().min() # maska musi byt nula...
    #mi = shift_intensity(mi, -int_offset)
        
    mytx = ants.registration(fixed=template_file, moving=mi, 
                                        verbose=False,
                                        type_of_transform='SyN',
                                        syn_metric='demons',
                                        reg_iterations=[1200, 1200, 1200, 1200])

    wi = ants.apply_transforms(fixed=template_file, moving=mi,
                                    transformlist=mytx['fwdtransforms'])
    
    print(f'center of wi: {ants.get_center_of_mass(wi)}')
    print(wi.min())
    print(wi.max())

    MI = ants.image_mutual_information(template_file, wi)
        
    print('{:} MI similarity: {:2.5f}'.format(filename, MI))
    print('--------------------------------------------------')
    #wi = shift_intensity(wi, int_offset)
    ants.image_write(wi, aligned_model_mha)
        
        
    afftxfwd = ants.read_transform(mytx['fwdtransforms'][1])#, dimension=3)
    warptxfwd = ants.image_read(mytx['fwdtransforms'][0])

    ants.write_transform(afftxfwd, afn_fwd)
    ants.image_write(warptxfwd, warp_fwd)

    afftxinv = ants.read_transform(mytx['invtransforms'][0])#, dimension=3)
    warptxinv = ants.image_read(mytx['invtransforms'][1])

    ants.write_transform(afftxinv, afn_inv)
    ants.image_write(warptxinv, warp_inv)
        

        


