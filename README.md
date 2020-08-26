# I. File list
```
.
|    spatial_feature_calculator.py - Python script containing the spatial features model*
|    Dockerfile - Docker file to run python script

* Runs for all combinations of N_length and N_width values
```

# II. How to Run
1. Download the associated data at <insert url later>. Note, that this already contains both the inputs and outputs 
of the spatial features model.
2. Download and Run Docker Desktop. For more information on Docker visit: https://docs.docker.com/desktop/. To ensure 
that it is installed correctly go to the command prompt/terminal and enter $ docker --version
3. Change to the current working directory using command prompt/terminal $ cd <insert_path_to_\spatial_features_model>
4. Build the docker image by running $ docker build --tag spatialfeatures .
5. Run the image and mount the associated data you downloaded in step 1 by running (Note, this will take a long time)
$docker run -v <path_to_associated_data>\multiobjective_dam_hazard_io:/app_io spatialfeatures
