import os
import sys

from Maxar_OGC.auth import Auth
from Maxar_OGC.wms import WMS
from Maxar_OGC.wfs import WFS
from Maxar_OGC.wmts import WMTS
from Maxar_OGC.wcs import WCS
import Maxar_OGC.process as process
import requests
import warnings
import csv
from concurrent.futures import as_completed
from PIL import Image
from bs4 import BeautifulSoup as bs


warnings.filterwarnings("ignore")


class Interface:
    """
    The primary interface for interacting with the WMS and WFS OGC classes.
    Args:
        base_url (string) = The url that you are using ex. 'https://securewatch.digitalglobe.com/'
        connect_id (string) = The connectId tied to your account
        username (string) = The username if your connectId requires Auth
        password (string) = The password associated with your username
    """

    def __init__(self, *args):
        if len(args) > 0:
            try:
                base_url = args[0]
                connect_id = args[1]
            except:
                raise Exception("Must pass connectId with base_url")
            if len(args) == 4:
                username = args[2]
                password = args[3]
                self._session = Auth(base_url, connect_id, username, password).session_object
            else:
                self._session = Auth(base_url, connect_id).session_object
        else:
            self._session = Auth().session_object
        self.wms = WMS(self._session)
        self.wfs = WFS(self._session)
        self.wmts = WMTS(self._session)
        self.wcs = WCS(self._session)

    def search(self, bbox=None, srsname="EPSG:4326", filter=None, shapefile=False, csv=False, **kwargs):
        """
        Function searches using the wfs method.
        Args:
            bbox (string) = Bounding box of AOI. Comma delimited set of coordinates. (miny,minx,maxy,maxx)
            srsname (string) = Desired projection. Defaults to EPSG:4326
            filter (string) = CQL filter used to refine data of search.
            shapefile (bool) = Binary of whether or not to return as shapefile format
            csv (bool) = Binary of whether or not to return as csv format
        Kwargs:
            featureprofile (string) = The desired stacking profile. Defaults to account Default
            typename (string) = The typename of the desired feature type. Defaults to FinishedFeature. Example input
            MaxarCatalogMosaicProducts
        Returns:
            Response is either a list of features or a shapefile of all features and associated metdata.
        """
        # if filter:
        #     process.cql_checker(filter)
        if shapefile:
            result = self.wfs.search(bbox=bbox, filter=filter, srsname=srsname, outputformat='shape-zip', **kwargs)
        elif csv:
            result = self.wfs.search(bbox=bbox, filter=filter, srsname=srsname, outputformat='csv', **kwargs)
        else:
            result = self.wfs.search(bbox=bbox, filter=filter, srsname=srsname, **kwargs)
        if bbox:
            if shapefile:
                if 'download_path' in kwargs.keys():
                    return process.download_file(result, format_response='zip', download_path=kwargs['download_path'])
                else:
                    return process.download_file(result, format_response='zip')
            elif csv:
                if 'download_path' in kwargs.keys():
                    return process.download_file(result, format_response='csv', download_path=kwargs['download_path'])
                else:
                    return process.download_file(result, format_response='csv')
            else:
                if 'typename' in kwargs.keys():
                    if 'MaxarCatalogMosaic' in kwargs['typename']:
                        return result.json()['features']
                result = process.aoi_coverage(bbox, result)
                return result['features']
        elif 'request' in kwargs.keys():
            if kwargs['request'] == 'DescribeFeatureType':
                result = self.wfs.search(bbox=bbox, filter=filter, **kwargs)
                return result.text

        else:
            if shapefile:
                if 'download_path' in kwargs.keys():
                    return process.download_file(result, format_response='zip', download_path=kwargs['download_path'])
                else:
                    return process.download_file(result, format_response='zip')
            elif csv:
                if 'download_path' in kwargs.keys():
                    return process.download_file(result, format_response='csv', download_path=kwargs['download_path'])
                else:
                    return process.download_file(result, format_response='csv')
            else:
                return result.json()['features']

    def download_image(self, bbox=None, srsname="EPSG:4326", height=None, width=None, img_format=None, identifier=None,
                       gridoffsets=None, zoom_level=None, download=True, outputpath=None, display=True,
                       **kwargs):
        """
        Function downloads the image using the wms method.
        Args:
            bbox (string) = Bounding box of AOI. Comma delimited set of coordinates. (miny,minx,maxy,maxx)
            srsname (string) = Desired projection. Defaults to EPSG:4326
            height (int) = The vertical number of pixels to return
            width (int) = The horizontal number of pixels to return
            img_format (string) = The format of the response image either jpeg, png or geotiff
            identifier (string) = The feature id
            gridoffsets (string) = The pixel size to be returned in X and Y dimensions
            zoom_level (int) = The zoom level. Used for WMTS
            download (bool) = User option to download band manipulation file locally.
            outputpath (string) = Output path must include output format. Downloaded path default is user home path.
        Kwargs:
            legacyid (string) = The duc id to download the browse image
        Returns:
            requests response object or downloaded file path
        """
        img_formatted = process._check_image_format(img_format)

        if 'legacyid' in kwargs.keys():
            legacy_id = kwargs['legacyid']
            url = "https://api.discover.digitalglobe.com/show?id={}".format(legacy_id)
            result = requests.request("GET", url, headers={}, data={})
        elif zoom_level:
            if not bbox:
                raise Exception('zoom_level must have a bbox')
            else:
                process._validate_bbox(bbox, srsname=srsname)
                wmts_list = self.wmts.wmts_bbox_get_tile_list(zoom_level, bbox, crs=srsname)
                return wmts_list
        elif identifier:
            if not gridoffsets or not bbox:
                raise Exception('Identifiers must have gridoffset and bbox')
            else:
                result = self.wcs.return_image(bbox, identifier, gridoffsets, srsname=srsname)
                if outputpath:
                    file_name = process.download_file(result, download_path=outputpath)
                else:
                    file_name = process.download_file(result, format_response=img_format)
                return self.wcs.parse_coverage(file_name)
        else:
            if not bbox or not img_format or not width or not height:
                raise Exception('height/width must have a bbox and an img_format')
            else:
                process._validate_bbox(bbox, srsname=srsname)
                result = self.wms.return_image(bbox=bbox, srsname=srsname, format=img_formatted, height=height, width=width, **kwargs)
        if display:
            process._display_image(result)
        if download:
            if outputpath:
                file_name = process.download_file(result, download_path=outputpath)
            else:
                file_name = process.download_file(result, format_response=img_format)
            return f"Downloaded file {file_name}"
        else:
            return result

    def download_browse_image(self, input_id, img_format='jpeg', outputpath=None, display=False):
        """
        Function downloads the browse image for the desired legacy id
        Args:
            input_id (string) = The desired input id (Can be feature id or catalog id)
            img_format (string) = The format of the response image either jpeg, png or geotiff
            outputpath (string) = Output path must include output format. Downloaded path default is user home path.
            display (bool) = Display image in IDE (Jupyter Notebooks only)
        Returns:
            Downloaded image location of desired legacy id in desired format
        """

        legacyid = self._convert_feature_to_legacy(input_id)
        process._check_image_format(img_format)
        url = "https://api.discover.digitalglobe.com/show?id={}".format(legacyid)
        result = requests.request("GET", url, headers={}, data={})
        if display:
            process._display_image(result)
        if outputpath:
            file_name = process.download_file(result, download_path=outputpath)
        else:
            file_name = process.download_file(result, format_response=img_format)
        return f"Downloaded file {file_name}"

    def get_tile_list_with_zoom(self, bbox, zoom_level, srsname="EPSG:4326"):
        """
        Function acquires a list of tile calls dependent on the desired bbox and zoom level
        Args:
            bbox (string) = Bounding box of AOI. Comma delimited set of coordinates. (miny,minx,maxy,maxx)
            zoom_level (int) = The zoom level
            srsname (string) = Desired projection. Defaults to EPSG:4326
        Returns:
            List of individual tile calls for desired bbox and zoom level
        """

        process._validate_bbox(bbox, srsname=srsname)
        wmts_list = self.wmts.wmts_bbox_get_tile_list(zoom_level, bbox, crs=srsname)
        return wmts_list

    def download_tiles(self, bbox, zoom_level, srsname="EPSG:4326", img_format='jpeg', outputpath=None, display=False):
        """
        Function downloads all tiles within a bbox dependent on zoom level
        Args:
            bbox (string) = Bounding box of AOI. Comma delimited set of coordinates. (miny,minx,maxy,maxx)
            zoom_level (int) = The zoom level
            srsname (string) = Desired projection. Defaults to EPSG:4326
            img_format (string) = The format of the response image either jpeg, png or geotiff
            outputpath (string) = Output path must include output format. Downloaded path default is user home path.
            display (bool) = Display image in IDE (Jupyter Notebooks only)
        Returns:
            Message displaying success and location of downloaded tiles
        """
        process._check_image_format(img_format)
        wmts = self.get_tile_list_with_zoom(bbox, zoom_level, srsname=srsname)[1]
        if outputpath:
            extension = outputpath.split(".")[-1]
            base_file = outputpath.replace("." + extension, "")
        else:
            extension = img_format
            base_file = os.getcwd() + "\\Download"
        for tile in wmts:
            response = self.wmts.wmts_get_tile(tile[0], tile[1], tile[2], crs=srsname)
            if display:
                process._display_image(response)
            filename = "{}_{}_{}_{}.{}".format(base_file, tile[0], tile[1], tile[2], extension)
            with open(filename, 'wb+') as f:
                f.write(response.content)
        return "Download complete, files are located in {}".format(base_file)

    def download_image_with_feature_id(self, bbox, identifier, gridoffsets, srsname="EPSG:4326", img_format='jpeg',
                                       display=True, outputpath=None):
        """
        Function downloads the image and metadata of desired feature id
        Args:
            bbox (string) = Bounding box of AOI. Comma delimited set of coordinates. (miny,minx,maxy,maxx)
            identifier (string) = Desired feature id
            gridoffsets (string) = The pixel size to be returned in X and Y dimensions
            srsname (string) = Desired projection. Defaults to EPSG:4326
            img_format (string) = The format of the response image either jpeg, png or geotiff
            outputpath (string) = Output path must include output format. Downloaded path default is user home path.
        Returns:
            Downloaded image location of desired feature id in desired format and associated metadata
        """

        process._check_image_format(img_format)
        result = self.wcs.return_image(bbox, identifier, gridoffsets, srsname=srsname)

        if display:
            process._display_image(result)

        if outputpath:
            file_name = process.download_file(result, download_path=outputpath)
        else:
            file_name = process.download_file(result, format_response=img_format)
        return self.wcs.parse_coverage(file_name)

    def download_image_by_pixel_count(self, bbox, height, width, srsname="EPSG:4326", img_format='jpeg', outputpath=None,
                                      display=False, **kwargs):
        """
        Function downloads the image of desired bbox dependent on pixel height and width
        Args:
            bbox (string) = Bounding box of AOI. Comma delimited set of coordinates. (miny,minx,maxy,maxx)
            height (int) = The vertical number of pixels to return
            width (int) = The horizontal number of pixels to return
            srsname (string) = Desired projection. Defaults to EPSG:4326
            img_format (string) = The format of the response image either jpeg, png or geotiff
            outputpath (string) = Output path must include output format. Downloaded path default is user home path.
            display (bool) = Display image in IDE (Jupyter Notebooks only)
        Kwargs:
            filter (string) = CQL filter used to refine data of search.
            featureprofile (string) = The desired stacking profile. Defaults to account Default
            bands (list[string]) = The desired band combination of 1-4 items. Requires SWIR 8 Band or MS1_MS2
        Returns:
            Downloaded image location of desired bbox dependent on pixel height and width
        """

        img_formatted = process._check_image_format(img_format)
        process._validate_bbox(bbox, srsname=srsname)
        result = self.wms.return_image(bbox=bbox, srsname=srsname, format=img_formatted, height=height, width=width, **kwargs)
        if display:
            process._display_image(result)

        if outputpath:
            file_name = process.download_file(result, download_path=outputpath)
        else:
            file_name = process.download_file(result, format_response=img_format)
        return "Downloaded file {}".format(file_name)

    def band_manipulation(self, bbox, featureid, band_combination, srsname="EPSG:4326", height=256, width=256,
                          img_format='jpeg', display=True, outputpath=None):
        """
        Function changes the bands of the feature id passed in.
        Args:
            bbox (string) = Bounding box of AOI. Comma delimited set of coordinates. (miny,minx,maxy,maxx)
            featureid (string) = The id of the image
            band_combination (list[string]) = The desired band combination of 1-4 items.
            srsname (string) = Desired projection. Defaults to EPSG:4326
            height (int) = The vertical number of pixels to return
            width (int) = The horizontal number of pixels to return
            image_format (string) = The file type that you want downloaded.
            outputpath (string) = Output path must include output format. Downloaded path default is user home path.
        Returns:
            download location for file
        """

        band_string = self._band_check(featureid, band_combination)
        feature_id_filter = "featureId='{}'".format(featureid)
        message = self.download_image_by_pixel_count(bbox, height, width, srsname=srsname, img_format=img_format,
                                                     outputpath=outputpath, display=display, filter=feature_id_filter,
                                                     bands=band_string)
        return message

    def get_image_from_csv(self, featureid, img_size=1024, **kwargs):
        """
        Function reruns requests for images that previously failed, from a csv file
        Args:
            featureid (string) = Feature id of the image
            img_size (int) = Desired pixel resolution (size x size). Defaults to 1024
        kwargs:
            outputdirectory (string) = Desired output location for tiles
        Returns:
            None
        """
        if 'outputdirectory' not in kwargs.keys():
            outputdirectory = os.path.expanduser('~')
        else:
            outputdirectory = kwargs['outputdirectory']
        url = self.wms.base_url
        headers = self.wms.headers
        querstring = self.wms.querystring
        querstring['width'] = img_size
        querstring['height'] = img_size
        querstring['coverage_cql_filter'] = "featureId='{}'".format(featureid)
        if 'image_format' in kwargs.keys():
            format = kwargs['image_format']
            querstring['format'] = 'image/{}'.format(format)
        else:
            format = querstring['format'][6:]
        failed_reqs = []
        with open(os.path.join(outputdirectory, 'failed_tiles.csv'), "r") as csvfile:
            request_reader = csv.reader(csvfile, delimiter=',')
            for row in request_reader:
                for r in row:
                    sub_bbox1, sub_bbox2, sub_bbox3, sub_bbox4, sub_grid_cell_location = r.split(", ")
                    sub_bbox = sub_bbox1 + ", " + sub_bbox2 + ", " + sub_bbox3 + ", " + sub_bbox4
                    sub_query = querstring.copy()
                    sub_query['bbox'] = sub_bbox
                    sub_response = requests.request("GET", url, params=sub_query, headers=headers)
                    if sub_response.status_code == 200:
                        sub_output = os.path.join(outputdirectory,
                                                      sub_grid_cell_location + ".{}".format(format))
                        process.download_file(sub_response, download_path=sub_output)
                        print('request from csv succeeded for image ' + sub_grid_cell_location)
                    else:
                        print('request from csv failed for image ' + sub_grid_cell_location)
                        failed_reqs.append(r)
        csvfile.close()
        os.remove(os.path.join(outputdirectory, 'failed_tiles.csv'))
        if len(failed_reqs) > 0:
            with open(os.path.join(outputdirectory, 'failed_tiles.csv'), "w", newline='') as csvfile:
                tile_writer = csv.writer(csvfile, delimiter=',')
                for fr in failed_reqs:
                    tile_writer.writerow([fr])

    def get_full_res_image(self, featureid, thread_number=100, bbox=None, mosaic=False, img_size=1024,
                           srsname='EPSG:4326', **kwargs):
        """
        Function takes in a feature id and breaks the image up into 1024x1024 tiles, then places a number of calls
        based on multithreading percentages to return a full image strip in multiple tiles
        Args:
            featureid (string) = Feature id of the image
            thread_number (int) = Number of threads given to multithread functionality
            bbox (string) = Bounding box of AOI. Comma delimited set of coordinates. (miny,minx,maxy,maxx)
            mosaic (bool) = Flag if image files are mosaiced
            img_size (int) = Desired pixel resolution (size x size). Defaults to 1024
            srsname (string) = Desired projection. Defaults to EPSG:4326
        kwargs:
            outputdirectory (string) = Desired output location for tiles
            image_format (string) = Desired image format (png or jpeg)
        Returns:
            None
        """

        if bbox is not None:
            process._validate_bbox(bbox, srsname=srsname)
        filter = "featureId='{}'".format(featureid)
        if kwargs.get('search_result'):
            wfs_request = kwargs['search_result']
        else:
            wfs_request = self.search(filter=filter, srsname=srsname)
        image_bbox = wfs_request[0]['geometry']['coordinates'][0]
        x_coords = [x[0] for x in image_bbox]
        y_coords = [y[1] for y in image_bbox]

        if srsname == "EPSG:4326":
            miny = min(y_coords)
            maxy = max(y_coords) + 0.0042176
            minx = min(x_coords)
            maxx = max(x_coords) + 0.0054932
        else:
            miny = min(y_coords)
            maxy = max(y_coords) + 468.1536
            minx = min(x_coords)
            maxx = max(x_coords) + 468.1536

        if bbox is not None:
            bbox_order = bbox.split(',')
            if srsname == "EPSG:4326":
                miny = max(miny, float(bbox_order[0]))
                maxy = min(maxy, float(bbox_order[2])) + 0.0042176
                minx = max(minx, float(bbox_order[1]))
                maxx = min(maxx, float(bbox_order[3])) + 0.0054932
            else:
                miny = max(miny, float(bbox_order[0]))
                maxy = min(maxy, float(bbox_order[2])) + 468.1536
                minx = max(minx, float(bbox_order[1]))
                maxx = min(maxx, float(bbox_order[3])) + 468.1536

        y_list = []
        x_list = []

        if srsname == "EPSG:4326":
            while miny < maxy:
                y_list.append(miny)
                miny += 0.0042176
            while minx < maxx:
                x_list.append(minx)
                minx += 0.0054932
            tiles = {}

            if len(y_list) == 1:
                if len(x_list) == 1:
                    tiles['c{}_r{}'.format(0, 0)] = '{}, {}, {}, {}'.format(y_list[0], x_list[0],
                                                                            y_list[0] + 0.0042176, x_list[0] + 0.0054932)
                else:
                    for x in range(len(x_list) - 1):
                        tiles['c{}_r{}'.format(x, 0)] = '{}, {}, {}, {}'.format(y_list[0], x_list[x], y_list[0] + 0.0042176,
                                                                                x_list[x + 1])
            elif len(x_list) == 1:
                for y in reversed(range(len(y_list) - 1)):
                    tiles['c{}_r{}'.format(0, len(y_list) - y - 2)] = '{}, {}, {}, {}'.format(y_list[y], x_list[0],
                                                                                              y_list[y + 1],
                                                                                              x_list[0] + 0.0054932)
            else:
                for y in reversed(range(len(y_list) - 1)):
                    for x in range(len(x_list) - 1):
                        tiles['c{}_r{}'.format(x, len(y_list) - y - 2)] = '{}, {}, {}, {}'.format(y_list[y], x_list[x],
                                                                                                  y_list[y + 1],
                                                                                                  x_list[x + 1])

        else:
            while miny < maxy:
                y_list.append(miny)
                # How many decimal degrees being incremented by, converted DD to Meters, which is 111km is 1DD at the equator
                # 111 * 0.0042176 is equal to 0.4681536 km then multiplied by 1000 to get 468.1536 Meters
                miny += 468.1536
            while minx < maxx:
                x_list.append(minx)
                minx += 468.1536
            tiles = {}

            if len(y_list) == 1:
                if len(x_list) == 1:
                    tiles['c{}_r{}'.format(0, 0)] = '{}, {}, {}, {}'.format(x_list[0], y_list[0],
                                                                            x_list[0] + 468.1536, y_list[0] + 468.1536)
                else:
                    for x in range(len(x_list) - 1):
                        tiles['c{}_r{}'.format(x, 0)] = '{}, {}, {}, {}'.format(x_list[x], y_list[0],
                                                                                x_list[x + 1], y_list[0] + 468.1536)
            elif len(x_list) == 1:
                for y in reversed(range(len(y_list) - 1)):
                    tiles['c{}_r{}'.format(0, len(y_list) - y - 2)] = '{}, {}, {}, {}'.format(x_list[0], y_list[y],
                                                                                              x_list[0] + 468.1536,
                                                                                              y_list[y + 1])
            else:
                for y in reversed(range(len(y_list) - 1)):
                    for x in range(len(x_list) - 1):
                        tiles['c{}_r{}'.format(x, len(y_list) - y - 2)] = '{}, {}, {}, {}'.format(x_list[x], y_list[y],
                                                                                                  x_list[x + 1],
                                                                                                  y_list[y + 1])

        print("Started full image download process...")

        #This section deletes bboxes that don't cover the image from Tiles
        # wfs_Response = self.wfs.search(filter=filter, srsname=srsname)

        # if bbox is not None:
        #     if process.aoi_coverage(bbox, wfs_Response)['features'][0]['bbox_coverage'] == 0:
        #         raise Exception("Bounding box is outside of desired feature's AOI")
        # keysToDel = []
        # for tile, tile_bbox in tiles.items():
        #     if srsname == "EPSG:4326":
        #         bbox_coverage = process.aoi_coverage(tile_bbox, wfs_Response)['features'][0]['coverage']
        #     else:
        #         tile_bbox_list = [i for i in tile_bbox.split(',')]
        #         sub_bbox = ",".join([tile_bbox_list[1], tile_bbox_list[0], tile_bbox_list[3], tile_bbox_list[2], srsname])
        #         bbox_coverage = process.aoi_coverage(sub_bbox + ",{}".format(srsname), wfs_Response)['features'][0]['coverage']
        #     if bbox_coverage == 0.0:
        #         keysToDel.append(tile)

        # for tileKey in keysToDel:
        #     del tiles[tileKey]


        url = self.wms.base_url
        headers = self.wms.headers
        querstring = self.wms.querystring
        querstring['crs'] = srsname
        querstring['width'] = img_size
        querstring['height'] = img_size
        querstring['coverage_cql_filter'] = "featureId='{}'".format(featureid)
        if 'image_format' in kwargs.keys():
            format = kwargs['image_format']
            querstring['format'] = 'image/{}'.format(format)
        else:
            format = querstring['format'][6:]


        def response_thread(coord_list):
            """
            Function multithreads requests to speed up image return process
            Args:
                coord_list (list) = Coordinates for individual tiles
            Returns:
                List of cell locations and corresponding response objects
            """
            failed_request = []
            sub_bbox, sub_grid_cell_location = coord_list.split("|")
            sub_query = querstring.copy()
            sub_query['bbox'] = sub_bbox
            sub_response = requests.request("GET", url, params=sub_query, headers=headers)
            if sub_response.status_code != 200:
                failed_request.append(coord_list)
            return [sub_grid_cell_location, sub_response, failed_request]


        def split_array_and_send_requests(array, num_attempts):
            """

            Function splits the array into chucks and executes the response_thread function using the
            thread pool executor, then downloads the image file if the request is successful. If requests
            fail, the function retries requests for those tiles until they succeed

            Args:
                array (list) = List of tiles with corresponding coordinates
                num_attempts (int) = Number of times rerunning the requests has been attempted

            """

            failed_reqs = []
            chunk_size = thread_number * 5
            chunk_count = int(len(array) / chunk_size)

            for i in range(chunk_count + 1):
                if i == chunk_count:
                    sub_array = array[i * chunk_size:]
                else:
                    sub_array = array[i * chunk_size:(i + 1) * chunk_size]
                with process.BoundedThreadPoolExecutor(max_workers=thread_number) as executor:
                    futures = [executor.submit(response_thread, coords) for coords in sub_array]
                    for future in as_completed(futures):
                        coord, response, failed_request = future.result()
                        if response.status_code == 200:
                            sub_output = os.path.join(outputdirectory, coord + ".{}".format(format))
                            process.download_file(response, download_path=sub_output)
                        else:
                            for fr in failed_request:
                                failed_reqs.append(fr)
                print('Finished section {} out of {}'.format(i + 1, chunk_count + 1))
                print('\r')
            if len(failed_reqs) > 0:
                if num_attempts < 10:
                    num_attempts += 1
                    print('Some image requests failed, retrying failed requests, retry attempt {}'.format(num_attempts))
                    print('\r')
                    split_array_and_send_requests(failed_reqs, num_attempts)
                else:
                    print('Attempted failed image requests 10 times, will print failed requests to csv and retry')
                    print('\r')
                    with open(os.path.join(outputdirectory, 'failed_tiles.csv'), "w", newline='') as csvfile:
                        failed_tile_writer = csv.writer(csvfile, delimiter=',')
                        for fr in failed_reqs:
                            row_content = fr.replace("|", ", ")
                            failed_tile_writer.writerow([row_content])
                    csvfile.close()
            failed_reqs.clear()
            print('\r')
            print('\n')

        multithreading_array = ["{}|{}".format(k, j) for j, k in list(tiles.items())]
        if 'outputdirectory' not in kwargs.keys():
            outputdirectory = os.path.expanduser('~')
        else:
            outputdirectory = kwargs['outputdirectory']
        with open(os.path.join(outputdirectory, 'Grid_cell_coordinates.txt'), 'w') as grid_coords:
            grid_coords.write('grid_cell_name | grid_cell_bbox\n')
            for line in multithreading_array:
                value, key = line.split('|')
                grid_coords.write('{} | {}\n'.format(key, value))

        split_array_and_send_requests(multithreading_array, num_attempts=0)

        if mosaic:
            print("Finished full image download process, output directory is: {}. Beginning mosaic process".
                format(os.path.split(outputdirectory)[0]))
            self.create_mosaic(base_dir=kwargs['outputdirectory'], img_size=img_size, img_format=format, **kwargs)
        else:
            return "Finished full image download process, output directory is: {}".\
                format(os.path.split(outputdirectory)[0])

    def create_mosaic(self, base_dir, img_format, img_size=1024, **kwargs):
        '''
        Function creates a mosaic of downloaded image tiles from full_res_dowload function
        Args:
            base_dir (string) = Root directory containing image files to be mosaiced
            img_format (string) = Image format of files
            img_size (int) = Size of individual image files, defaults to 1024
        Kwargs:
            outputdirectory (string) = Directory destination of finished mosaic file
            filename (string) = filename of merged image
        Returns:
            None
        '''

        if img_format == 'geotiff':
            try:
                import rasterio
                from rasterio.merge import merge
                from rasterio.errors import RasterioIOError
            except:
                self._pillow_mosaic(base_dir, img_format, img_size=1024, **kwargs)
                print("GDAL is not installed on your machine. The downloaded image will not be georeferenced. "
                              " Please refer to the Maxar_OGC documentation for steps on how to install GDAL in "
                              "your environment.")
            else:
                srcs_to_mosaic = []
                for image in os.listdir(base_dir):
                    if image.endswith('.geotiff'):
                        filename = os.path.join(base_dir, image)
                        try:
                            raster = rasterio.open(filename)
                            output_data = raster.meta.copy()
                            raster.close()
                        except RasterioIOError:
                            print(f'Skipping bad tile {image}')
                            continue
                        srcs_to_mosaic.append(filename)
                mosaic, output = merge(srcs_to_mosaic)
                output_data.update(
                    {"driver": "GTiff",
                     "height": mosaic.shape[1],
                     "width": mosaic.shape[2],
                     "transform": output,
                     "compress": "lzw",
                     "tiled": True,
                     "blockxsize": 512,
                     "blockysize": 512,

                     }
                )
                factors = [2]
                while min(mosaic.shape[1], mosaic.shape[2]) / factors[-1] >= 1024:
                    factors.append(factors[-1] * 2)

                if 'outputdirectory' in kwargs.keys():
                    if 'filename' in kwargs.keys():
                        with rasterio.open(os.path.join(
                                kwargs['outputdirectory'], kwargs['filename'] + '.geotiff'), "w", **output_data) as m:
                            m.write(mosaic)
                            m.build_overviews(factors, rasterio.enums.Resampling.gauss)
                            m.update_tags(ns='rio_overview', resampling='gauss')
                        print("Finished image mosaic process, output directory is: {}".format(kwargs['outputdirectory']))
                    else:
                        with rasterio.open(os.path.join(
                                kwargs['outputdirectory'], 'merged_image.geotiff'), "w", **output_data) as m:
                            m.write(mosaic)
                            m.build_overviews(factors, rasterio.enums.Resampling.gauss)
                            m.update_tags(ns='rio_overview', resampling='gauss')
                        print("Finished image mosaic process, output directory is: {}".format(kwargs['outputdirectory']))
                else:
                    if 'filename' in kwargs.keys():
                        with rasterio.open(os.path.join(base_dir, kwargs['filename'] + '.geotiff'), "w", **output_data) as m:
                            m.write(mosaic)
                            m.build_overviews(factors, rasterio.enums.Resampling.gauss)
                            m.update_tags(ns='rio_overview', resampling='gauss')
                    else:
                        with rasterio.open(os.path.join(base_dir, 'merged_image.geotiff'), "w", **output_data) as m:
                            m.write(mosaic)
                            m.build_overviews(factors, rasterio.enums.Resampling.gauss)
                            m.update_tags(ns='rio_overview', resampling='gauss')
                    print("Finished image mosaic process, output directory is: {}".format(base_dir))
        else:
            self._pillow_mosaic(base_dir, img_format, img_size=1024, **kwargs)

    def _pillow_mosaic(self, base_dir, img_format, img_size=1024, **kwargs):
        '''
                Function creates a mosaic of downloaded image tiles from full_res_dowload function
                Args:
                    base_dir (string) = Root directory containing image files to be mosaiced
                    img_format (string) = Image format of files
                    img_size (int) = Size of individual image files, defaults to 1024
                Kwargs:
                    outputdirectory (string) = Directory destination of finished mosaic file
                    filename (string) = filename of merged image
                Returns:
                    None
                '''

        Image.MAX_IMAGE_PIXELS = None
        coord_list = []
        for k in [i for i in os.listdir(base_dir) if ".txt" not in i and os.path.isfile(os.path.join(base_dir, i))]:
            filename = k
            coords = k.replace('c', '').replace('_r', ',').replace('.{}'.format(img_format), '').split(',')
            if "geotiff" in filename:
                pre, ext = os.path.splitext(os.path.join(base_dir, filename))
                os.rename(os.path.join(base_dir, filename), pre + ".tiff")
                filename = filename.replace("geotiff", "tiff")
            coord_list.append([filename, int(coords[0]), int(coords[1])])

        max_row = max([i[2] for i in coord_list]) + 1
        max_col = max([i[1] for i in coord_list]) + 1
        maximum = max(max_col, max_row)
        size = img_size * maximum
        mosaic = Image.new('RGB', (max_col * img_size, max_row * img_size), (size, size, size))

        count = 0
        for i in coord_list:
            column = img_size * i[1]
            row = img_size * i[2]
            mosaic.paste(Image.open(os.path.join(base_dir, i[0])), (column, row))
            count += 1
            if count % 100 == 0:
                sys.stdout.write("Processing {} of {} total".format(count, len(coord_list)))
                sys.stdout.write("\r")

        # must change to tiff because pillow doesnt support geotiff
        if img_format == "geotiff":
            img_format = "tiff"
        # if they specify filename, give it a name. Else, call it merged image
        if 'outputdirectory' in kwargs.keys():
            if 'filename' in kwargs.keys():
                filepath = r"{}\{}.{}".format(kwargs['outputdirectory'], kwargs['filename'], img_format)
                mosaic.save(filepath)
                print("Finished image mosaic process, output directory is: {}".format(kwargs['outputdirectory']))
            else:
                filepath = r"{}\merged_image.{}".format(kwargs['outputdirectory'], img_format)
                mosaic.save(filepath)
                print("Finished image mosaic process, output directory is: {}".format(kwargs['outputdirectory']))
        else:
            if 'filename' in kwargs.keys():
                filepath = r"{}\{}.{}".format(base_dir, kwargs['filename'], img_format)
                mosaic.save(filepath)
            else:
                filepath = r"{}\merged_image.{}".format(base_dir, img_format)
                mosaic.save(filepath)
            print("Finished image mosaic process, output directory is: {}".format(base_dir))

    def get_filter_parameters(self, typename):
        """
        Function lists all available filter parameters for a given typename
        Args:
            typename (string) = The typename of the desired feature type
        Returns:
            Dictionary of filter parameters for desired feature type
        """

        search = self.search(typename=typename, request='DescribeFeatureType')
        soup = bs(search, 'xml')
        elements = soup.find_all('xsd:element')
        my_dict = {}
        for element in elements:
            name = element['name']
            type = element['type'].split(':')[1]
            my_dict[name] = type
        my_dict.pop(typename)
        return my_dict

    def _band_check(self, featureid, band_combination):
        """
        Function checks bands given against a list of valid bands
        Args:
            featureid (string) = The id of the image
            band_combination (list[string]) = The desired band combination of 1-4 items.
        Returns:
            String of band combination
        """
        band_check = self.search(filter="featureId='{}'".format(featureid))
        band_check_list = ['MS1_MS2', 'SWIR 8-Band']
        if band_check[0]['properties']['productType'] not in band_check_list:
            raise Exception('Product Type for the image must be either SWIR 8-band or MS1_MS2.')
        band_options = ['R', 'G', 'B', 'C', 'Y', 'RE', 'N', 'N2', 'S1', 'S2', 'S3', 'S4', 'S5', 'S6', 'S7']
        if len(band_combination) <= 0 or len(band_combination) > 4:
            raise Exception('The number of bands must be greater than 0 and less than or equal to 4.')

        band_string = ','.join([i if i in band_options else 'z' for i in band_combination])

        if 'z' in band_string:
            raise Exception(band_combination + ' is not a valid option.')
        return band_string

    def _convert_feature_to_legacy(self, input_id):
        """
        Function takes in a feature id or legacy id and finds the browse image associated with it.
        Args:
            input_id (string) = The id that you are searching for
        Returns:
            Legacy id of desired feature
        """

        catalog_identifiers = ['101', '102', '103', '104', '105', '106']

        # if the id passed in is a cat id or WVO4 Inv id. Return the browse for that id from discover api
        if input_id[0:3] in catalog_identifiers or '-inv' == input_id[-4:]:
            legacy_id = input_id
        # If the id passed in is a feature id. Use our wfs method to return a json and parse out the legacy id from
        # the metadata
        else:
            json_return = self.search(filter="featureId='{}'".format(input_id))
            legacy_id = json_return[0]['properties']['legacyId']
        return legacy_id

    @staticmethod
    def calculate_sqkm(bbox, srsname="EPSG:4326"):
        """
        Function calculates the area in square kilometers of the desired bounding box
        Args:
            bbox (string) = Bounding box of AOI. Comma delimited set of coordinates. (miny,minx,maxy,maxx)
            srsname (string) = Desired projection. Defaults to EPSG:4326
        Returns:
            Float of bounding box area in square kilometers
        """
        
        area = process.area_sqkm(bbox, srsname=srsname)
        return area
