# Import statements
import arcpy
import numpy as np
import datetime
import time

# Class to handle the cases where the data is not found
class DoesNotCompute(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

# Function to check if the data exists in the preprocessing geodatabase
def check_preprocessing_files():
    arcpy.AddMessage("-------------------------")
    try:
        # Check for elevation data
        if arcpy.Exists("MODEL_DTM"):
            elevation = "MODEL_DTM"
            arcpy.AddMessage("Elevation data detected")
            arcpy.AddMessage("-------------------------")
        else:
            # Raise a custom exception
            raise DoesNotCompute("elevation (DTM)")

        # Check and confirm the land cover file / type
        if arcpy.Exists("MODEL_Landcover_LCM"):            
            land_cover = "MODEL_Landcover_LCM"
            land_cover_type = 'LCM 2007'
            arcpy.AddMessage("LCM 2007 land cover data detected")
            arcpy.AddMessage("-------------------------")

            if arcpy.Exists("MODEL_Landcover_LCM_Altered"):
                land_cover = "MODEL_Landcover_LCM_Altered"
                land_cover_type = 'LCM 2007'
                arcpy.AddMessage("Altered LCM land cover detected and selected")
                arcpy.AddMessage("-------------------------")
        elif arcpy.Exists("MODEL_Landcover_CORINE"):
            land_cover = "MODEL_Landcover_CORINE"
            land_cover_type = 'CORINE 2006'
            arcpy.AddMessage("CORINE 2006 land cover data detected")
            arcpy.AddMessage("-------------------------")

            if arcpy.Exists("MODEL_Landcover_CORINE_Altered"):
                land_cover = "MODEL_Landcover_CORINE_Altered"
                land_cover_type = 'CORINE 2006'
                arcpy.AddMessage("Altered CORINE land cover detected and selected")
                arcpy.AddMessage("-------------------------")

        elif arcpy.Exists("MODEL_COMBINE_LC"):
            land_cover = "MODEL_COMBINE_LC"
            land_cover_type = 'COMBINE'
            arcpy.AddMessage("Natural England SPS and LCM 2007 combined land cover data detected")
            arcpy.AddMessage("-------------------------")

            if arcpy.Exists("MODEL_COMBINE_LC_Altered"):
                land_cover = "MODEL_COMBINE_LC_Altered"
                land_cover_type = 'COMBINE'
                arcpy.AddMessage("Altered Natural England SPS and LCM 2007 land cover detected and selected")
                arcpy.AddMessage("-------------------------")
        else:
            raise DoesNotCompute("land cover data")

        # Check and confirm the host soil file / type
        if arcpy.Exists("MODEL_Soil_HOST"):
            soil = "MODEL_Soil_HOST"
            soil_type = "HOST"
            arcpy.AddMessage("HOST soil data detected")
            arcpy.AddMessage("-------------------------")
        elif arcpy.Exists("MODEL_Soil_FAO"):
            soil = "MODEL_Soil_FAO"
            soil_type = "FAO"
            arcpy.AddMessage("FAO soil data detected")
            arcpy.AddMessage("-------------------------")
        else:
            raise DoesNotCompute("soil data")

        # Check and confirm the grainsize proportions    
        if arcpy.Exists("MODEL_GS1"):
            grain_size_1_proportion = "MODEL_GS1"
            
        if arcpy.Exists("MODEL_GS2"):
            grain_size_2_proportion = "MODEL_GS2"

        if arcpy.Exists("MODEL_GS3"):
            grain_size_3_proportion = "MODEL_GS3"

        if arcpy.Exists("MODEL_GS4"):
            grain_size_4_proportion = "MODEL_GS4"

        if arcpy.Exists("MODEL_GS5"):
            grain_size_5_proportion = "MODEL_GS5"

        if arcpy.Exists("MODEL_GS6"):
            grain_size_6_proportion = "MODEL_GS6"

        if arcpy.Exists("MODEL_GS7"):
            grain_size_7_proportion = "MODEL_GS7"
            arcpy.AddMessage("Grain size proportions data detected")
            arcpy.AddMessage("-------------------------")            
        else:
            raise DoesNotCompute("grain size proportions")  

        if arcpy.Exists("MODEL_river_soil_depth"):
            river_soil_depth = "MODEL_river_soil_depth"
            arcpy.AddMessage("River soil depth data detected")  
            arcpy.AddMessage("-------------------------")            
        else:
            raise DoesNotCompute("river soil depth")

    except DoesNotCompute as error:        
        arcpy.AddError("Model data: " + str(error.value) + " from the pre-processing script could not be found at the location you specified") 
           
        
    return elevation, land_cover, land_cover_type, soil, soil_type, grain_size_1_proportion, grain_size_2_proportion, grain_size_3_proportion, grain_size_4_proportion, grain_size_5_proportion, grain_size_6_proportion, grain_size_7_proportion, river_soil_depth

# Function to the average number of days rainfall per year based on the input textfile
def average_days_rainfall(precipitation_textfile):
    total_number_days = 0
    total_day_precip = 0

    # Open the precipitation file
    precip_read = open(precipitation_textfile)

    for precip in precip_read:
        total_number_days += 1
        if float(precip) >= 0.1:
            total_day_precip += 1
        if total_number_days == 1456 or total_number_days == 2913:
            total_number_days += 1
    
    years_of_sim = total_number_days / 364.25
    day_pcp_yr = total_day_precip / years_of_sim
          
    arcpy.AddMessage("Average number of days precipitation per year is " + str(day_pcp_yr))
    arcpy.AddMessage("-------------------------")  
    precip_read.close()

    return day_pcp_yr

# Function to convert the date into a day of the year
def convert_date_day_year(current_date):
    month_and_day = datetime.datetime.strptime(current_date, '%d/%m/%Y')
    day = int(month_and_day.strftime('%j'))
    return day

# Function to calculate the locations that have an active layer
def calculate_active_layer(river_soil_depth, cell_size):
    
    # Locate areas which need an active layer (everywhere else should be 0.0)
    active_layer = np.zeros_like(river_soil_depth, dtype = float)
    np.putmask(active_layer, river_soil_depth > 0, 0.2)
     
    # Calculate the remaining soil depth at that location
    inactive_layer = river_soil_depth - active_layer

    # Convert active layer to volume:
    active_layer = active_layer * cell_size * cell_size

    # Convert active layer to volume:
    inactive_layer = inactive_layer * cell_size * cell_size 

    # Covnert NoData to -9999
    inactive_layer[river_soil_depth == -9999] = -9999
    active_layer[river_soil_depth == -9999] = -9999

    arcpy.AddMessage("Calculated active layer and remaining soil depth in the river channel") 
    arcpy.AddMessage("-------------------------") 
    return active_layer, inactive_layer

# Function to calculation the default grain size volumes in m2
def get_grain_volumes(grain_size_proportions, active_layer):
        
    # List to store grain size volumes
    grain_size_volumes =[]

    # Iterate through the list of grain size volumes
    for proportion in grain_size_proportions:
        volume = np.zeros_like(proportion, dtype = float)
        volume = active_layer * proportion
        volume[active_layer == -9999] = -9999
        grain_size_volumes.append(volume)

    arcpy.AddMessage("Calculated starting grain size volumes") 
    arcpy.AddMessage("-------------------------") 
    return grain_size_volumes

# Function to create and store the temporary file locations on the harddrive of the computer
def temporary_file_locations(numpy_array_location, grain_size_proportions, grain_size_volumes):

    # create temporary file location for grain_proportions
    grain_pro_temp_1 = numpy_array_location + '\grain_pro_1.npy'
    grain_pro_temp_2 = numpy_array_location + '\grain_pro_2.npy'
    grain_pro_temp_3 = numpy_array_location + '\grain_pro_3.npy'
    grain_pro_temp_4 = numpy_array_location + '\grain_pro_4.npy'
    grain_pro_temp_5 = numpy_array_location + '\grain_pro_5.npy'
    grain_pro_temp_6 = numpy_array_location + '\grain_pro_6.npy'
    grain_pro_temp_7 = numpy_array_location + '\grain_pro_7.npy'
    
    grain_pro_temp_list = [grain_pro_temp_1, grain_pro_temp_2, grain_pro_temp_3, grain_pro_temp_4, grain_pro_temp_5, grain_pro_temp_6, grain_pro_temp_7]

    remaining_soil_grain_pro_temp_1 = numpy_array_location + '\grain_rpro_1.npy'
    remaining_soil_grain_pro_temp_2 = numpy_array_location + '\grain_rpro_2.npy'
    remaining_soil_grain_pro_temp_3 = numpy_array_location + '\grain_rpro_3.npy'
    remaining_soil_grain_pro_temp_4 = numpy_array_location + '\grain_rpro_4.npy'
    remaining_soil_grain_pro_temp_5 = numpy_array_location + '\grain_rpro_5.npy'
    remaining_soil_grain_pro_temp_6 = numpy_array_location + '\grain_rpro_6.npy'
    remaining_soil_grain_pro_temp_7 = numpy_array_location + '\grain_rpro_7.npy'

    remaining_soil_pro_temp_list = [remaining_soil_grain_pro_temp_1, remaining_soil_grain_pro_temp_2, remaining_soil_grain_pro_temp_3, remaining_soil_grain_pro_temp_4, remaining_soil_grain_pro_temp_5, remaining_soil_grain_pro_temp_6, remaining_soil_grain_pro_temp_7]

    # create temproary file locations for the grain volumes
    grain_vol_temp_1 = numpy_array_location + '\grain_vol_temp_1.npy'
    grain_vol_temp_2 = numpy_array_location + '\grain_vol_temp_2.npy'
    grain_vol_temp_3 = numpy_array_location + '\grain_vol_temp_3.npy'
    grain_vol_temp_4 = numpy_array_location + '\grain_vol_temp_4.npy'
    grain_vol_temp_5 = numpy_array_location + '\grain_vol_temp_5.npy'
    grain_vol_temp_6 = numpy_array_location + '\grain_vol_temp_6.npy'
    grain_vol_temp_7 = numpy_array_location + '\grain_vol_temp_7.npy'

    grain_vol_temp_list = [grain_vol_temp_1, grain_vol_temp_2, grain_vol_temp_3, grain_vol_temp_4, grain_vol_temp_5, grain_vol_temp_6, grain_vol_temp_7]

    # Save the proportion arrays to disk
    np.save(grain_pro_temp_list[0], grain_size_proportions[0])
    np.save(grain_pro_temp_list[1], grain_size_proportions[1])
    np.save(grain_pro_temp_list[2], grain_size_proportions[2])
    np.save(grain_pro_temp_list[3], grain_size_proportions[3])
    np.save(grain_pro_temp_list[4], grain_size_proportions[4])
    np.save(grain_pro_temp_list[5], grain_size_proportions[5])
    np.save(grain_pro_temp_list[6], grain_size_proportions[6])

    arcpy.AddMessage("Saved proportions in active layer to disk")

    # Save the remaining soil proportion arrays to disk
    np.save(remaining_soil_pro_temp_list[0], grain_size_proportions[0])
    np.save(remaining_soil_pro_temp_list[1], grain_size_proportions[1])
    np.save(remaining_soil_pro_temp_list[2], grain_size_proportions[2])
    np.save(remaining_soil_pro_temp_list[3], grain_size_proportions[3])
    np.save(remaining_soil_pro_temp_list[4], grain_size_proportions[4])
    np.save(remaining_soil_pro_temp_list[5], grain_size_proportions[5])
    np.save(remaining_soil_pro_temp_list[6], grain_size_proportions[6])

    arcpy.AddMessage("Saved proportions in inactive layer to disk")

    # Save the grain volumes arrays to disk
    np.save(grain_vol_temp_list[0], grain_size_volumes[0])
    np.save(grain_vol_temp_list[1], grain_size_volumes[1])
    np.save(grain_vol_temp_list[2], grain_size_volumes[2])
    np.save(grain_vol_temp_list[3], grain_size_volumes[3])
    np.save(grain_vol_temp_list[4], grain_size_volumes[4])
    np.save(grain_vol_temp_list[5], grain_size_volumes[5])
    np.save(grain_vol_temp_list[6], grain_size_volumes[6])

    arcpy.AddMessage("Saved volumes to disk")

    return grain_pro_temp_list, grain_vol_temp_list, remaining_soil_pro_temp_list