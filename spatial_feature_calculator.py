# Pyqgis script to be run in Docker

# Import packages
import os
import pandas as pd
import numpy as np

# Specify Global Vars
pathto_data = '/app_io'
os.environ["QT_QPA_PLATFORM"] = "offscreen"

# Import core functions
from qgis.core import (QgsApplication, QgsProperty, QgsRasterLayer, QgsVectorLayer, QgsVectorFileWriter)
QgsApplication.setPrefixPath("/usr", False)
qgs = QgsApplication([], False)
qgs.initQgis()

# Import Native Algorithms
from qgis.analysis import QgsNativeAlgorithms
QgsApplication.processingRegistry().addProvider(QgsNativeAlgorithms())

# Import Processing Algorithms, append the path where processing plugin can be found
import sys
sys.path.append('/usr/share/qgis/python/plugins')
import processing
from processing.core.Processing import Processing
Processing.initialize()


def importer():
    """
    Function to import spatial datasets to QGIS vector layers
    :return: tuple[QgsVectorlayer, QgsVectorlayer, QgsRasterLayer]
                contains the drains, census, and slope datasets
    """
    # Import data
    drains = QgsVectorLayer(os.path.join(pathto_data, 'spatial_features_model','input', 'drains_w_daminfo.shp'), 'drains_w_daminfo', 'ogr')
    census = QgsVectorLayer(os.path.join(pathto_data, 'spatial_features_model','input', 'census.shp'), 'census blocks', 'ogr')
    slope = QgsRasterLayer(os.path.join(pathto_data, 'spatial_features_model','input', 'slope.tiff'))
    # Export data
    return drains, census, slope


def to_df(vl):
    """
    Convert the attribute table of a QGIS vector layer to Pandas dataframe
    :param vl: QgsVectorlayer
    :return: DataFrame
    """
    # List of lists constant feature values
    l = [i.attributes() for i in vl.getFeatures()]
    # List of fields
    fields_ls = [vl.fields()[i].name() for i in vl.attributeList()]
    # Create dataframe
    df = pd.DataFrame.from_records(l, columns=fields_ls)
    # Export
    return df
    

def get_spatial_feats(N_length, N_width, drains, census, slope, store):
    """
    Run the spatial features model for a given N_length and N_width value
    :param N_length: int
                        N_length value
    :param N_width: int
                        N_width value
    :param drains: QgsVectorlayer
                        Dataset of drains and corresponding dam information
    :param census: QgsVectorlayer
                        Dataset of census-block-level features
    :param slope: QgsRasterlayer
                        Dataset of slope values
    :param store: HDFStore
                        HDF5 object containing all the sets of spatial feature values
    :return: int
                        exit status
    """
    print(N_length, N_width)
    # Add N_length as field
    params = {'INPUT':drains,'FIELD_NAME':'N_length','FIELD_TYPE':0,'FIELD_LENGTH':10,'FIELD_PRECISION':3,'NEW_FIELD':True,'FORMULA':str(int(N_length)),'OUTPUT':'memory:drains'}
    downstream_centers = processing.run("qgis:fieldcalculator", params)['OUTPUT']
    # Add N_width as field
    params = {'INPUT':downstream_centers,'FIELD_NAME':'N_width','FIELD_TYPE':0,'FIELD_LENGTH':10,'FIELD_PRECISION':3,'NEW_FIELD':True,'FORMULA':str(int(N_width)),'OUTPUT':'memory:drains'}
    downstream_centers = processing.run("qgis:fieldcalculator", params)['OUTPUT']
    # Downstream center: take length of drainage = height * N_length
    params = {'INPUT':downstream_centers,'START_DISTANCE':0,'END_DISTANCE':QgsProperty.fromExpression('"DAM_HEIGHT" * "N_length" ') ,'OUTPUT':'TEMPORARY_OUTPUT'} #Height is the 28th attribute TODO: make more generic
    downstream_centers = processing.run("native:linesubstring", params)['OUTPUT']
    # Downstream region: buffer downstream center = N_width (meters)
    params = {'INPUT':downstream_centers,'DISTANCE': QgsProperty.fromExpression('"DAM_HEIGHT" * "N_width"/2'),'SEGMENTS':5,'END_CAP_STYLE':0,'JOIN_STYLE':0,'MITER_LIMIT':2,'DISSOLVE':False,'OUTPUT':'memory:downstream_regions'}
    downstream_regions = processing.run("native:buffer", params)['OUTPUT']
    # Create Spatial Index for Downstream Regions
    processing.run("qgis:createspatialindex", {'INPUT': downstream_regions})
    # Maximum downstream slope
    params = {'INPUT_RASTER': slope, 'RASTER_BAND': 1, 'INPUT_VECTOR': downstream_regions, 'COLUMN_PREFIX': 'Slope_', 'STATISTICS': [6]}
    downstream_regions_w_stats = processing.run("qgis:zonalstatistics", params)#['INPUT_VECTOR']
    # Create Spatial Index for Downstream Regions
    processing.run("qgis:createspatialindex", {'INPUT': downstream_regions})
    # Sum of downstream house and population
    params = {'INPUT': downstream_regions, 'JOIN': census, 'PREDICATE': [0], 'JOIN_FIELDS': ['hous', 'pop', 'foot', 'cont', 'buil'], 'SUMMARIES': [5], 'DISCARD_NONMATCHING': False, 'OUTPUT': 'memory:downstream regions'}
    downstream_regions_w_stats = processing.run("qgis:joinbylocationsummary", params)['OUTPUT']
    # Convert to DataFrame
    df = to_df(downstream_regions_w_stats)
    # Extract only spatial features
    df = df[['N_length', 'N_width', 'Slope_max', 'hous_sum', 'pop_sum', 'foot_sum', 'cont_sum', 'buil_sum']]
    # Export Data
    store.put('N_length_'+str(N_length)+'_N_width_'+str(N_width), df)
    return 0    
    

def main():
    # Import data
    drains, census, slope = importer()
    # Create Spatial Index for Census
    processing.run("qgis:createspatialindex", {'INPUT': census})
    # Parameters to Loop Over
    N_length = np.arange(1, 81, 2)
    N_width = np.arange(1, 81, 2)
    # Create DataFrame with Combinations
    outlist = [(i, j) for i in N_length for j in N_width]
    df = pd.DataFrame(data=outlist, columns=['N_length','N_width'])
    # Create HDF5 Objective
    s = pd.HDFStore(os.path.join(pathto_data, 'spatial_features_model', 'output', 'spatial_feats.h5'))
    # Run Spatial Features Model
    df.apply(lambda row: get_spatial_feats(row[0], row[1], drains, census, slope, s), axis=1)
    s.close()
    return 0


if __name__ == '__main__':
    main()
