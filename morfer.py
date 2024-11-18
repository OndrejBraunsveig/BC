import os
import numpy as np
import pandas as pd
from scipy.spatial import distance_matrix
from concurrent.futures import ProcessPoolExecutor
from stl import mesh as stlmesh
import ants
import glob
from tqdm import trange
from .ct_mesher import stl_from_ct
import pyvista as pv
import math
from pathlib import Path


# Step 1: Generate the STL mesh from the template image
def compute_mesh(image, stl_file_name):
    lower_int = 0.1
    iter_num = 25
    relax = 0.15
    detail_level = 1.5
    stl_from_ct(image, lower_int, iter_num, relax, detail_level, stl_file_name, method='ACVD', ratio=15)

def morf(project_id):
    # Paths to input files and directories
    points_path = 'left_points.csv'
    #source = '/media/anatom/Nový svazek/osazovani_bodu/NM/demons/warped_dex/'
    template_path = 'T_3.mha'
    template_stl_path = 'T_morf_3.stl'
    #folder_path = "/media/anatom/Nový svazek/osazovani_bodu/NM/dex/"
    #cloud_points = '/media/anatom/Nový svazek/osazovani_bodu/template/'
    output_filename = f'results_{project_id}.csv'

# Load the reference points from the CSV file
    points = pd.read_csv(points_path)
    ref_points = points[['Points:0', 'Points:1', 'Points:2']].values
    orig_point_idx = points.index

    """
    # Load additional points from M6a.csv and M6b.csv
    points_M6a = pd.read_csv(os.path.join(cloud_points, 'M6a.csv'))
    points_M6b = pd.read_csv(os.path.join(cloud_points, 'M6b.csv'))
    ref_points_M6a = points_M6a[['X', 'Y', 'Z']].values
    ref_points_M6b = points_M6b[['X', 'Y', 'Z']].values

    # Combine all reference points
    ref_points = np.vstack((ref_points, ref_points_M6a, ref_points_M6b))
    orig_point_idx = np.concatenate([orig_point_idx, [-1] * (len(ref_points_M6a) + len(ref_points_M6b))])
    """

    # Get a list of all patient files in the source directory

    # Load the template image and generate the corresponding STL mesh
    template = ants.image_read(template_path)
    compute_mesh(template, template_stl_path)

    # Load the generated STL mesh
    mesh = pv.read(template_stl_path)

    all_points_trns = []

    # Step 2: Apply transformations to reference points for each patient
    patient = project_id
    aff_fwd_file = f"R_{patient}_afn_fwd.mat"
    warp_fwd_file = f"R_{patient}_warp_fwd.nii.gz"
    if os.path.exists(aff_fwd_file) and os.path.exists(warp_fwd_file):
        points_trns = ants.apply_transforms_to_points(dim=3, points=pd.DataFrame(ref_points, columns=['x', 'y', 'z']),
                                                    transformlist=[warp_fwd_file, aff_fwd_file], 
                                                    whichtoinvert=[False, False])
        print(patient)
        points_trns['ID'] = np.arange(len(points_trns))  # Assign unique IDs for transformed points
        points_trns['patient'] = patient
        points_trns['neighbor'] = 0
        points_trns['orig_point_idx'] = orig_point_idx
        all_points_trns.append(points_trns)
    else:
        print(f"Transform files for {patient} do not exist. Přeskakuji.")

    # Combine all transformed points and save them to a CSV file
    if all_points_trns:
        combined_points_trns = pd.concat(all_points_trns, ignore_index=True)
        combined_points_trns.to_csv(f'combined_transformed_points_{project_id}.csv', index=False)

    # Step 3: Load combined transformed points and perform distance calculations
    combined_points = pd.read_csv(f'combined_transformed_points_{project_id}.csv')

    # Function to calculate Euclidean distance between two points
    def calculate_distance(point1, point2):
        return np.sqrt(np.sum((point1 - point2) ** 2))

    # List of ID pairs for calculating distances (M1, M2, M5, etc.)
    id_pairs = [(0, 1), (2, 3), (4, 5), (6, 7), (8, 9), (8, 10), (11, 12), (13, 14)]

    # Initialize a dictionary to store the results for each patient
    results = {'patient': f'R_{patient}', 'M1': [], 'M2': [], 'M5': [], 'M6': [], 'M7': [], 'M8': [], 'M9': [], 'M10': [], 'M4': []}

    # Unique patients in the dataset
    unique_patients = combined_points['patient'].unique()

    # Calculate distances for each patient
    for patient in unique_patients:
        patient_data = combined_points[combined_points['patient'] == patient]
        
        # Initialize a dictionary to store distances for this patient
        patient_distances = {}
        
        for i, (id1, id2) in enumerate(id_pairs):
            # Extract points with the corresponding IDs
            point1 = patient_data[patient_data['ID'] == id1][['x', 'y', 'z']].values
            point2 = patient_data[patient_data['ID'] == id2][['x', 'y', 'z']].values
            
            # Ensure both points are available for distance calculation
            if len(point1) > 0 and len(point2) > 0:
                distance = calculate_distance(point1[0], point2[0])
                dimension = f'M{[1, 2, 5, 6, 7, 8, 9, 10][i]}'  # Map to M1, M2, M5, etc.
                patient_distances[dimension] = distance
        
        '''
        # Calculate M6 for this patient (maximum distance from M6a and M6b points)
        m6_points = patient_data[patient_data['orig_point_idx'] == -1][['x', 'y', 'z']].values
        if len(m6_points) > 1:
            m6_distances = distance_matrix(m6_points, m6_points)
            np.fill_diagonal(m6_distances, 0)  # Ignore self-distances
            max_m6_distance = np.max(m6_distances)
            patient_distances['M6'] = max_m6_distance
        else:
            patient_distances['M6'] = np.nan
        '''
        
        # Calculate M4 for this patient using Heron's formula
        point1_M4 = patient_data[patient_data['ID'] == 15][['x', 'y', 'z']].values
        point2_M4 = patient_data[patient_data['ID'] == 16][['x', 'y', 'z']].values
        point3_M4 = patient_data[patient_data['ID'] == 17][['x', 'y', 'z']].values

        # Ensure that we have all points for M4 calculation
        if len(point1_M4) > 0 and len(point2_M4) > 0 and len(point3_M4) > 0:
            a = calculate_distance(point1_M4[0], point2_M4[0])
            b = calculate_distance(point1_M4[0], point3_M4[0])
            c = calculate_distance(point2_M4[0], point3_M4[0])
            s = (a + b + c) / 2
            So = np.sqrt(s * (s - a) * (s - b) * (s - c))
            M4 = (2 * So) / c
        else:
            M4 = np.nan  # Handle missing points gracefully

        # Add distances for this patient to the results
        #results['patient'].append(patient)
        for dim in ['M1', 'M2', 'M5', 'M7', 'M8', 'M9', 'M10']:
            results[dim].append(patient_distances.get(dim, np.nan))  # Use NaN if distance is missing
        results['M6'].append(patient_distances.get('M6', np.nan))
        results['M4'].append(M4)  # Add M4 for this patient

    # Convert results to a DataFrame
    results_df = pd.DataFrame(results)

    """
    # Step 5: Process STL files to compute M3 distances
    def compute_max_distance(points):
        D = distance_matrix(points, points, p=2)
        D = D.astype(np.float32)
        indices = np.unravel_index(np.argmax(D, axis=None), D.shape)
        return points[indices[0]], points[indices[1]]

    def process_stl_file(file_path, max_points=20000):
        try:
            mesh_data = stlmesh.Mesh.from_file(file_path)
            vertices = mesh_data.vectors.reshape(-1, 3)

            if len(vertices) == 0:
                print(f"No vertices found in {file_path}.")
                return None, file_path

            # Limit the number of points for calculation
            sampled_indices = np.random.choice(len(vertices), min(len(vertices), max_points), replace=False)
            sampled_vertices = vertices[sampled_indices]

            point1, point2 = compute_max_distance(sampled_vertices)
            largest_distance = np.linalg.norm(point1 - point2)
            return largest_distance, file_path
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
            return None, file_path

    def process_files_parallel(file_paths, max_workers):
        data = []

        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(process_stl_file, file_path) for file_path in file_paths]

            for future in futures:
                largest_distance, file_path = future.result()
                if largest_distance is not None:
                    data.append({
                        "Model Name": os.path.basename(file_path),
                        "M3": largest_distance
                    })

        output_table = pd.DataFrame(data)
        return output_table

    # Adjust max_workers based on CPU count
    max_workers = min(os.cpu_count(), 20)

    # Collect STL files from the directory
    stl_files = [os.path.join(folder_path, file) for file in os.listdir(folder_path) if file.lower().endswith(".stl")]
    output_table = process_files_parallel(stl_files, max_workers)
    output_table.to_csv("M3_distance.csv", index=False)
    """
    # Merge M3 distances with the rest of the calculated results
    output_table = pd.read_csv(f'M3_distance_{project_id}.csv')
    output_table['Model Name'] = output_table['Model Name'].str.replace('.stl', '', regex=False)
    final_results = results_df.merge(output_table[['Model Name', 'M3']], left_on='patient', right_on='Model Name', how='left').drop(columns=['Model Name'])

    # Fill missing M3 values with NA
    final_results['M3'].fillna('NA', inplace=True)

    # Reorder columns to place M3 in the correct position
    final_results = final_results[['patient', 'M1', 'M2', 'M3', 'M4', 'M5', 'M6', 'M7', 'M8', 'M9', 'M10']]

    # Round all numerical values to 2 decimal places
    final_results.update(final_results.select_dtypes(include=[np.number]).round(2))

    # Save the final results
    final_results.to_csv(output_filename, sep=';', index=False)

    # Debugging output for verification
    print("Final results saved to:", output_filename)
    print(final_results.head())

    # Remove all files
    os.remove('T_3.stl')
    os.remove('T_3.mha')
    os.remove('T_morf_3.stl')
    os.remove(f'warped_R_{project_id}.mha')
    # upravit jmeno pri ukladani jeste
    os.remove(f'M3_distance_{project_id}.csv')
    os.remove(f'combined_transformed_points_{project_id}.csv')
    os.remove(f'R_{project_id}_afn_fwd.mat')
    os.remove(f'R_{project_id}_afn_inv.mat')
    os.remove(f'R_{project_id}_warp_fwd.nii.gz')
    os.remove(f'R_{project_id}_warp_inv.nii.gz')

    # prozatimni
    os.remove(f'results_{project_id}.csv')


