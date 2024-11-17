import os
import numpy as np
import pandas as pd
from scipy.spatial import distance_matrix
from stl import mesh as stlmesh

def compute_max_distance(points):
    D = distance_matrix(points, points, p=2)
    D = D.astype(np.float32)
    indices = np.unravel_index(np.argmax(D, axis=None), D.shape)
    return points[indices[0]], points[indices[1]]

def process_stl_file(file_path, max_points=20000):
    try:
        mesh_data = stlmesh.Mesh.from_file(file_path)
        vertices = mesh_data.vectors.reshape(-1, 3)

        # Omezení počtu bodů pro výpočet
        sampled_indices = np.random.choice(len(vertices), min(len(vertices), max_points), replace=False)
        sampled_vertices = vertices[sampled_indices]

        point1, point2 = compute_max_distance(sampled_vertices)
        largest_distance = np.linalg.norm(point1 - point2)
        return largest_distance
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return None

def process_files(file_path):
    data = []  # Seznam pro shromáždění dat

    largest_distance = process_stl_file(file_path)

    if largest_distance is not None:
        data.append({
            "Model Name": os.path.basename(file_path),
            "M3": largest_distance
        })

    output_table = pd.DataFrame(data)  # Vytvoření DataFrame ze seznamu dat
    return output_table

def M3_calc(project_id):
    file_path = f'R_{project_id}.stl'

    output_table = process_files(file_path)

    output_table.to_csv("M3_distance.csv", index=False)
    print("Processing completed. Output saved to M3_distance.csv")

