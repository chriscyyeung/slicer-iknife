import time
import argparse
import pyigtl
import numpy as np

from masslynx.MassLynxRawDefs import *
from masslynx.MassLynxRawReader import MassLynxException
from masslynx.MassLynxRawInfoReader import MassLynxRawInfoReader
from masslynx.MassLynxRawScanReader import MassLynxRawScanReader


def get_parser():
    parser = argparse.ArgumentParser(
        description="Real-time transfer of iKnife scan data to 3D Slicer "
                    "using the OpenIGTLink protocol."
    )
    parser.add_argument(
        "-i", 
        "--input",
        type=str, 
        required=True, 
        help="Path to the MassLynx raw data file."
    )
    parser.add_argument(
        "-p", 
        "--port", 
        type=int, 
        default=18946, 
        help="Output port number of the OpenIGTLink server."
    )
    parser.add_argument(
        "--type", 
        type=str, 
        default="TIC", 
        help="Type of scan data to send. Options: TIC or TOFM."
    )
    parser.add_argument(
        "--scan-device-name", 
        type=str, 
        default="iKnifeTIC", 
        help="Name of the output device for iKnife scans."
    )
    parser.add_argument(
        "--metadata-device-name", 
        type=str, 
        default="ScanMetadata", 
        help="Name of the output device for metadata."
    )
    return parser


def main(args):
    # initialize OpenIGTLink server
    output = pyigtl.OpenIGTLinkServer(port=args.port)
    
    # loop infinitely to send iKnife scan data to the server
    last_n_scans = 0
    while True:
        try:
            # create info reader to get raw details
            info_reader = MassLynxRawInfoReader(args.input)
            n_functions = info_reader.GetNumberofFunctions()
            functions = [info_reader.GetFunctionType(i) for i in range(n_functions)]
            tofm_function = functions.index(MassLynxFunctionType.TOFM)
            n_scans = info_reader.GetScansInFunction(tofm_function)
            
            # only send data if there are new scans
            if n_scans > last_n_scans:
                last_n_scans = n_scans

                # create scan reader from info reader and get last scan
                scan_reader = MassLynxRawScanReader(info_reader)
                masses, intensities = scan_reader.ReadScan(tofm_function, n_scans - 1)
                if args.type == "TOFM":
                    # merge, pad, and reshape data
                    data = np.column_stack((np.array(masses), np.array(intensities))).flatten()
                    reshape_size = int(np.floor(np.sqrt(data.size))) + 1
                    num_pad = reshape_size ** 2 - data.size
                    data = np.pad(data, (0, num_pad), "constant")
                    data = data.reshape((reshape_size, reshape_size))
                    scan_message = pyigtl.ImageMessage(data, device_name=args.scan_device_name)

                    # save scan number and padding amount for reshaping
                    metadata = {
                        "scan_number": n_scans,
                        "num_pad": num_pad
                    }
                    metadata_message = pyigtl.StringMessage(
                        str(metadata), device_name=args.metadata_device_name
                    )

                    # send messages
                    output.send_message(metadata_message, wait=True)
                    output.send_message(scan_message, wait=True)
                else:  # TIC
                    tic = np.sum(intensities)
                    tic_data = np.array([n_scans, tic])
                    tic_message = pyigtl.ImageMessage(tic_data, device_name=args.scan_device_name)
                    output.send_message(tic_message, wait=True)

        except MassLynxException as e:
            print(f"Masslynx error: {e.message}")
        
        except Exception as e:
            print(f"Error: {e}")
        
        finally:
            continue

    # # create info reader to get raw details
    # info_reader = MassLynxRawInfoReader(args.input)
    # n_functions = info_reader.GetNumberofFunctions()
    # functions = [info_reader.GetFunctionType(i) for i in range(n_functions)]
    # tofm_function = functions.index(MassLynxFunctionType.TOFM)
    # n_scans = info_reader.GetScansInFunction(tofm_function)

    # # loop through all scans
    # for i in range(n_scans):
    #     # create scan reader from info reader and get last scan
    #     scan_reader = MassLynxRawScanReader(info_reader)
    #     masses, intensities = scan_reader.ReadScan(tofm_function, i)
    #     if args.type == "TOFM":
    #         # merge, pad, and reshape data
    #         data = np.column_stack((np.array(masses), np.array(intensities))).flatten()
    #         reshape_size = int(np.floor(np.sqrt(data.size))) + 1
    #         num_pad = reshape_size ** 2 - data.size
    #         data = np.pad(data, (0, num_pad), "constant")
    #         data = data.reshape((reshape_size, reshape_size))
    #         scan_message = pyigtl.ImageMessage(data, device_name=args.scan_device_name)

    #         # save scan number and padding amount for reshaping
    #         metadata = {
    #             "scan_number": n_scans,
    #             "num_pad": num_pad
    #         }
    #         metadata_message = pyigtl.StringMessage(
    #             str(metadata), device_name=args.metadata_device_name
    #         )

    #         # send messages
    #         output.send_message(metadata_message, wait=True)
    #         output.send_message(scan_message, wait=True)
    #     else:  # TIC
    #         tic = np.sum(intensities)
    #         tic_data = np.array([i, tic])
    #         tic_message = pyigtl.ImageMessage(tic_data, device_name=args.scan_device_name)
    #         output.send_message(tic_message, wait=True)

    #     # simulate real-time data transfer
    #     time.sleep(0.5)


if __name__ == "__main__":
    parser = get_parser()
    main(parser.parse_args())
