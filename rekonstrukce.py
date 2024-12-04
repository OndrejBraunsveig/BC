import pymeshlab as ml
import os

def reconstruction(project_model_filename):

    filepath = f'{project_model_filename}.stl'

    # Load mesh from stl file
    ms = ml.MeshSet()
    ms.load_new_mesh(filepath)

    # Apply poisson when mesh has > 60000 vertexes
    vertex_count = ms.current_mesh().vertex_number()
    print(f'{vertex_count} vertex points')
    if (vertex_count > 60000):
        ms.load_filter_script('skript.mlx')
        ms.apply_filter_script()

        print('Poisson applied')

    # Apply decimation
    ms.load_filter_script('skript_decim.mlx')
    ms.apply_filter_script()

    # Save reduced mesh
    ms.save_current_mesh(f'R_{filepath}')

    # Remove non reduced stl file
    os.remove(filepath)
