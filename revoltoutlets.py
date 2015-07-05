#!/usr/bin/python
#
# Script to control the revolt-power px-1672 outlets via usb with the provided dongle.
# usage python revolt...py <action> <id>

# based on the pyusb tutorial script

import usb.core
import usb.util
import binascii
import math
import argparse


ACTION_VALUES = {
    "on1": 15,
    "off1": 14,
    "on2": 13,
    "off2": 12,
    "on3": 11,
    "off3": 10,
    "on4": 9,
    "off4": 8,
    "on5": 7,
    "off5": 6,
    "on6": 5,
    "off6": 4,
    "on7": 3,  # has no off7 counterpart!
    "ona": 2,
    "offa": 1,
    "off8": 0,  # has no on8 counterpart!
}


def find_revolt_endpoint():
    # find our device
    device = usb.core.find(idVendor=0xffff, idProduct=0x1122)

    # was it found?
    if device is None:
        raise ValueError('Device not found')

    # set the active configuration. With no arguments, the first
    # configuration will be the active one
    device.set_configuration()

    # get an endpoint instance
    device_configuration = device.get_active_configuration()
    interface_number = device_configuration[(0, 0)].bInterfaceNumber
    #usb.util.claim_interface(device, interface_number)
    alternate_setting = usb.control.get_interface(device, interface_number)
    interface = usb.util.find_descriptor(
        device_configuration, bInterfaceNumber=interface_number,
        bAlternateSetting=alternate_setting
    )

    endpoint = usb.util.find_descriptor(
        interface,
        # match the first OUT endpoint
        custom_match=(lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_OUT)
    )

    assert endpoint is not None

    return endpoint


def prepare_message(frame_id, frame_count, command):
    msgpart_frame_count = hex(frame_count).split('x')[1].ljust(2, '0')  #

    # convert the id to hex but get rid of the '0x' at the beginning to be able to
    # concatenate the message and make sure there are 4 characters (1 byte in hex)
    msgpart_id = hex(frame_id).split('x')[1].ljust(4, '0')

    msgpart_padding = "20"  # not relevant padding

    msgpart_end = "0000"  # unknown, not relevant

    if command in ACTION_VALUES:
        raw_action = ACTION_VALUES[command]

    else:
        raise ValueError('unknown action: %s' % command)

    msgpart_action = hex(raw_action).split('x')[1].ljust(2, '0')

    # compute the checksum: byte01+02+03+04 mod 256 have to be 255
    checksum = int(msgpart_id[:2], 16) + int(msgpart_id[2:], 16) + raw_action * 16
    raw_checksum = int(math.ceil(checksum / 256.0) * 256) - checksum - 1
    msgpart_checksum = hex(raw_checksum).split('x')[1].ljust(2, '0')

    message = msgpart_id + msgpart_action + msgpart_checksum + msgpart_padding + msgpart_frame_count + msgpart_end

    return message


def argparse_frame_count_constraints(value):
    intvalue = int(value)
    if intvalue < 1 or intvalue > 255:
        raise argparse.ArgumentTypeError('Frame transmission count not in range (1 to 255): %s' % value)
    return intvalue


def argparse_frame_id_constraints(value):
    intvalue = int(value)
    if intvalue < 0 or intvalue > 65535:
        raise argparse.ArgumentTypeError('Frame ID not in range (0 to 65535): %s' % value)
    return intvalue


def main():
    # the original software knows 3 parameters
    # Bit Width 100+6*50 seems not to be used, doesn't change the message

    # ID 0-65535
    default_raw_id = 6789
    default_frame_count = 2  # 3-255 number of sent frames (resend)

    parser = argparse.ArgumentParser()
    parser.add_argument("command", nargs='+')
    parser.add_argument("--verbose", "-v", help="increase output verbosity")
    parser.add_argument("--tx-count", "-n", type=argparse_frame_count_constraints, default=default_frame_count,
                        help='Number of frame transmissions. More transmissions increase chance that the outlet '
                             'receives them, but also increases transmission duration. Defaults to 2.')
    parser.add_argument("--id", "-i", type=argparse_frame_id_constraints, default=default_raw_id,
                        help='Frame ID (0 - 65535). Can be used to control multiple sets of outlets. Defaults to 6789.')
    args = parser.parse_args()

    frame_count = args.tx_count
    raw_id = args.id

    if not args.command:
        raise ValueError('No action specified')

    if args.verbose:
        print('Using ID %d' % raw_id)
        print('Requesting %d frame transmissions' % frame_count)

    endpoint = find_revolt_endpoint()

    for command in args.command:
        message = prepare_message(raw_id, frame_count, command)

        if args.verbose:
            print 'sending command %s (0x%s)' % (command, message)

        # write the data
        endpoint.write(binascii.a2b_hex(message))

    #usb.util.release_interface(device, interface_number)


if __name__ == "__main__":
    main()
