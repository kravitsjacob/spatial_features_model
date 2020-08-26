FROM qgis/qgis
WORKDIR /app
COPY ["spatial_feature_calculator.py","/app/"]
RUN apt-get install python-pip -y
RUN pip3 install pandas
RUN pip3 install numpy
RUN pip3 install tables
ENTRYPOINT ["python3", "-u", "spatial_feature_calculator.py"]
