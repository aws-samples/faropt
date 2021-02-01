import math
import numpy as np
import pandas as pd
import boto3
from botocore.exceptions import ClientError
from io import StringIO
from ortools.constraint_solver import pywrapcp
from ortools.constraint_solver import routing_enums_pb2
import json
import utils

class RoutingOpt(object):
    """RoutingOpt class for vehicle routing problem. This class computes a feasible and optimal solution for assigning routes to vehicles, given a set of locations to be visited and vehicle starting locations. The goal of the optimization problem is to minimize the overall distance traveled while making sure each location is visited exactly once.
    """

    def __init__(self, region_name, bucket_name, vehicles_file, locations_file, output_file, max_distance, stackname='faropt'):
        """Constructor method: Gets buckets and tables associated with the already launched stack. In addition it also gets the S3 location and names for data abd output files.
        :param region_name: Name of the S3 bucket region
        :type region_name: string
        :param bucket_name: Name of the S3 bucket
        :type bucket_name: string
        :param vehicles_file: Name (and path) of the csv file with vehicles' starting locations (Lat, Long)
        :type vehicles_file: string
        :param locations_file: Name (and path) of the csv file with locations to be visited (Lat, Long)
        :type locations_file: string
        :param output_file: Name (and path) of the output csv file with final routes computed by the optimizer
        :type output_file: string
        """
        
        self.region_name = region_name
        self.bucket_name = bucket_name
        self.max_distance = max_distance

        self.data_vehicles = self.read_file(region_name, bucket_name, vehicles_file)
        data_locations = self.read_file(region_name, bucket_name, locations_file)
        self.output_file = output_file
        self.matrix = {}

        #self.data_vehicles = pd.read_csv("../../../../faropt_vrp_data/vehicles.csv")
        data = self.create_data_array(data_locations, self.data_vehicles)
        self.locations = data[0]
        self.starting_locs = data[1]

        self.num_vehicles = self.data_vehicles.shape[0]
        self.num_locations = len(self.locations)
        self.num_start_locations = self.starting_locs.shape[0]
        vehicle_start_locations = []
        for k in range(0, self.num_vehicles):
            this_vehicle_loc = np.array([self.data_vehicles.iloc[k]['Lat'], self.data_vehicles.iloc[k]['Long']])
            x = np.where((self.starting_locs == this_vehicle_loc).all(axis=1))
            d_index = int(x[0][0])
            vehicle_start_locations.append(d_index)

        self.manager = pywrapcp.RoutingIndexManager(len(self.locations), self.num_vehicles, vehicle_start_locations,
                                                    vehicle_start_locations)


    
    
    def read_file(self,region_name, bucket_name, file_name):
            """Read file method: Reads the data from locations and vehicles files.
           :param region_name: Name of the S3 bucket region
           :type region_name: string
           :param bucket_name: Name of the S3 bucket
           :type bucket_name: string
           :param file_name: Path and name of the file to be read
           :type file_name: string
           """
            s3client = boto3.client('s3', region_name=region_name)
            csv_obj = s3client.get_object(Bucket=bucket_name, Key=file_name)
            body = csv_obj['Body']
            csv_string = body.read().decode('utf-8')
            df = pd.read_csv(StringIO(csv_string))
            return df
    
    def write_file(self, output):
        """Write file method: Write the output file to S3.
       :param file_name: Path and name of the output file to be written to S3
       :type file_name: string
       """
        csv_buffer = StringIO()
        output.to_csv(csv_buffer)
        s3_resource = boto3.resource('s3')
        s3_resource.Object(self.bucket_name, self.output_file).put(Body=csv_buffer.getvalue())
    
    
    def distance(self,lat1, long1, lat2, long2):
        """Computes the haversine distance between two points with given latitudes and langitudes.
        :param lat1: Latitude of the first point
        :type lat1: float
        :param long1: Longitude of the first point
        :type long1: float
        :param lat2: Latitude of the second point
        :type lat2: float
        :param long2: Longitude of the second point
        :type long2: float
        """
        # Note: The formula used in this function is not exact, as it assumes
        # the Earth is a perfect sphere.
    
        # Mean radius of Earth in miles
        radius_earth = 3959
    
        # Convert lat and long to
        # spherical coordinates in radians.
        degrees_to_radians = math.pi / 180.0
        phi1 = lat1 * degrees_to_radians
        phi1 = lat1 * degrees_to_radians
        phi2 = lat2 * degrees_to_radians
        lambda1 = long1 * degrees_to_radians
        lambda2 = long2 * degrees_to_radians
        dphi = phi2 - phi1
        dlambda = lambda2 - lambda1
    
        a = self.sine_component(dphi) + math.cos(phi1) * math.cos(phi2) * self.sine_component(dlambda)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        d = np.ceil(1.4 * radius_earth * c)
        return d
    
    def sine_component(self, angle):
        """Computes the sine component of the haversine formula
        :param angle: Angle in radians
        :type angle: float
        """
        h = math.sin(angle / 2) ** 2
        return h
    
    def create_data_array(self, df_locations, df_vehicles):
        """Method to extract unique locations from the data frames
        :param df_locations: data frame with locations that are to be visited by the vehicles
        :type df_locations: pandas.DataFrame
        :param df_vehicles: data frame with starting locations of the vehicles
        :type df_vehicles: pandas.DataFrame
        """
        a = np.array(df_vehicles[['Lat', 'Long']])
        b = np.ascontiguousarray(a).view(np.dtype((np.void, a.dtype.itemsize * a.shape[1])))
        _, idx = np.unique(b, return_index=True)
        unique_a = a[idx]
    
        locations = list()
        for k in range(0, unique_a.shape[0]):
            locations.append(list(unique_a[k, :]))
        starting_locs = np.copy(locations)
    
        for k in range(0, df_locations.shape[0]):
            lat_long = [df_locations.Lat.iloc[k], df_locations.Long.iloc[k]]
            locations.append(lat_long)
    
        data = [locations, starting_locs]
        return data
    
    def create_distance_matrix(self):
        """Method to compute the pair-wise distances between all the locations
        """
        for from_node in range(self.num_locations):
            self.matrix[from_node] = {}
            for to_node in range(self.num_locations):
                if from_node == to_node:
                    self.matrix[from_node][to_node] = 0
                else:
                    x1 = self.locations[from_node][0]
                    y1 = self.locations[from_node][1]
                    x2 = self.locations[to_node][0]
                    y2 = self.locations[to_node][1]
                    self.matrix[from_node][to_node] = self.distance(x1, y1, x2, y2)
    
    def distance_callback(self, from_index, to_index):
        """Returns the distance between the two nodes. This method is used by the routing manager
        :param from_index: Index of location 1 in distance_matrix
        :type from_index: int
        :param to_index: Index of location 2 in distance_matrix
        :type to_index: int
        """
        from_node = self.manager.IndexToNode(from_index)
        to_node = self.manager.IndexToNode(to_index)
        return self.matrix[from_node][to_node]
    
    def optimize(self):
        """Method to add the constraints and call the optimizer"""
        routing = pywrapcp.RoutingModel(self.manager)
        search_parameters = pywrapcp.DefaultRoutingSearchParameters()
        search_parameters.first_solution_strategy = (routing_enums_pb2.FirstSolutionStrategy.PATH_MOST_CONSTRAINED_ARC)
    
        data = {}
        self.create_distance_matrix()
        data['distance_matrix'] = self.matrix
        data['num_vehicles'] = self.num_vehicles
    
        transit_callback_index = routing.RegisterTransitCallback(self.distance_callback)
        routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)
    
        fix_start_cumul_to_zero = False
    
        dimension_name = 'Distance'
        routing.AddDimension(transit_callback_index,
                             0,
                             self.max_distance,
                             fix_start_cumul_to_zero,
                             dimension_name)
        distance_dimension = routing.GetDimensionOrDie(dimension_name)
        distance_dimension.SetGlobalSpanCostCoefficient(100)
    
        solution = routing.SolveWithParameters(search_parameters)
    
        if solution:
            print('Solution after search:')
            self.print_solution(data, routing, solution)
            self.write_solution(data, self.manager, routing, solution)
        else:
            print("No solution found")
    
    def write_solution(self, data, manager, routing, solution):
        """Method to write the solution to a csv file in S3 bucket
        :param data: data matrix consisting of number of vehicles and the distance matrix
        :type data: list
        :param manager: routing manager
        :type manager: pywrapcp.RoutingIndexManager
        :param routing: Routing model
        :type routing: pywrapcp.RoutingModel
        :param solution: Solution for the optimization problem
        :type solution: routing.Assignment
        """
        max_nodes = 0
        for vehicle_id in range(data['num_vehicles']):
            num_nodes = 0
            index = routing.Start(vehicle_id)
            while not routing.IsEnd(index):
                num_nodes = num_nodes + 1
                index = solution.Value(routing.NextVar(index))
    
            if num_nodes > max_nodes:
                max_nodes = num_nodes
    
        column_names = []
        for i in range(max_nodes+1):
            column_names.append('location_{}_lat'.format(i))
            column_names.append('location_{}_long'.format(i))
            column_names.append('location_{}_distance'.format(i))
    
        output = pd.DataFrame("", index = np.arange(self.num_vehicles), columns = column_names)
    
        for vehicle_id in range(data['num_vehicles']):
            index = routing.Start(vehicle_id)
            route_distance = 0
    
            i = 0
            while not routing.IsEnd(index):
                location_number = manager.IndexToNode(index)
                output['location_{}_lat'.format(i)][vehicle_id] = self.locations[location_number][0]
                output['location_{}_long'.format(i)][vehicle_id] = self.locations[location_number][1]
                output['location_{}_distance'.format(i)][vehicle_id] = route_distance
                previous_index = index
                index = solution.Value(routing.NextVar(index))
                route_distance += routing.GetArcCostForVehicle(previous_index, index, vehicle_id)
                i = i + 1
    
            location_number = manager.IndexToNode(index)
            output['location_{}_lat'.format(i)][vehicle_id] = self.locations[location_number][0]
            output['location_{}_long'.format(i)][vehicle_id] = self.locations[location_number][1]
            output['location_{}_distance'.format(i)][vehicle_id] = route_distance
        self.write_file(output)
    
    
    def print_solution(self, data, routing, solution):
        """Method to print the solution
        :param data: data matrix consisting of number of vehicles and the distance matrix
        :type data: list
        :param manager: routing manager
        :type manager: pywrapcp.RoutingIndexManager
        :param routing: Routing model
        :type routing: pywrapcp.RoutingModel
        :param solution: Solution for the optimization problem
        :type solution: routing.Assignment
        """
        max_route_distance = 0
        for vehicle_id in range(data['num_vehicles']):
            index = routing.Start(vehicle_id)
            plan_output = 'Route for vehicle {}:\n'.format(vehicle_id)
            route_distance = 0
            while not routing.IsEnd(index):
                plan_output += ' {} -> '.format(self.manager.IndexToNode(index))
                previous_index = index
                index = solution.Value(routing.NextVar(index))
                route_distance += routing.GetArcCostForVehicle(
                    previous_index, index, vehicle_id)
            plan_output += '{}\n'.format(self.manager.IndexToNode(index))
            plan_output += 'Distance of the route: {}m\n'.format(route_distance)
            print(plan_output)
            max_route_distance = max(route_distance, max_route_distance)
        print('Maximum of the route distances: {}m'.format(max_route_distance))

if __name__=="main":
    
    inputs = json.load('inputs.json')
    ro = RoutingOpt(region_name=inputs.region_name,
                    bucket_name=inputs.bucket_name,
                    vehicles_file=inputs.vehicles_file,
                    locations_file=inputs.locations_file,
                    output_file=inputs.output_file,
                    max_distance=inputs.max_distance,
                    stackname='faropt')
    ro.optimize()
    