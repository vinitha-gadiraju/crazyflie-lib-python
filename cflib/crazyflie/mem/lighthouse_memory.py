# -*- coding: utf-8 -*-
#
# ,---------,       ____  _ __
# |  ,-^-,  |      / __ )(_) /_______________ _____  ___
# | (  O  ) |     / __  / / __/ ___/ ___/ __ `/_  / / _ \
# | / ,--'  |    / /_/ / / /_/ /__/ /  / /_/ / / /_/  __/
#    +------`   /_____/_/\__/\___/_/   \__,_/ /___/\___/
#
# Copyright (C) 2019 - 2020 Bitcraze AB
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, in version 3.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
import logging
import struct

from .memory_element import MemoryElement

logger = logging.getLogger(__name__)


class LighthouseBsGeometry:
    """Container for geometry data of one Lighthouse base station"""

    SIZE_FLOAT = 4
    SIZE_BOOL = 1
    SIZE_VECTOR = 3 * SIZE_FLOAT
    SIZE_GEOMETRY = (1 + 3) * SIZE_VECTOR + SIZE_BOOL

    def __init__(self):
        self.origin = [0.0, 0.0, 0.0]
        self.rotation_matrix = [
            [0.0, 0.0, 0.0],
            [0.0, 0.0, 0.0],
            [0.0, 0.0, 0.0],
        ]
        self.valid = False

    def set_from_mem_data(self, data):
        self.origin = self._read_vector(
            data[0 * self.SIZE_VECTOR:1 * self.SIZE_VECTOR])
        self.rotation_matrix = [
            self._read_vector(data[1 * self.SIZE_VECTOR:2 * self.SIZE_VECTOR]),
            self._read_vector(data[2 * self.SIZE_VECTOR:3 * self.SIZE_VECTOR]),
            self._read_vector(data[3 * self.SIZE_VECTOR:4 * self.SIZE_VECTOR]),
        ]
        self.valid = struct.unpack('<?', data[4 * self.SIZE_VECTOR:])[0]

    def add_mem_data(self, data):
        self._add_vector(data, self.origin)
        self._add_vector(data, self.rotation_matrix[0])
        self._add_vector(data, self.rotation_matrix[1])
        self._add_vector(data, self.rotation_matrix[2])
        data += struct.pack('<?', self.valid)

    def _add_vector(self, data, vector):
        data += struct.pack('<fff', vector[0], vector[1], vector[2])

    def _read_vector(self, data):
        x, y, z = struct.unpack('<fff', data)
        return [x, y, z]

    def dump(self):
        print('origin:', self.origin)
        print('rotation matrix:', self.rotation_matrix)
        print('valid:', self.valid)


class LighthouseCalibrationSweep:
    def __init__(self):
        self.phase = 0.0
        self.tilt = 0.0
        self.curve = 0.0
        self.gibmag = 0.0
        self.gibphase = 0.0
        self.ogeemag = 0.0
        self.ogeephase = 0.0

    def dump(self):
        print(('phase: {}, tilt: {}, curve: {}, gibmag: {}, ' +
               'gibphase: {}, ogeemag: {}, ogeephase: {}').format(
            self.phase,
            self.tilt,
            self.curve,
            self.gibmag,
            self.gibphase,
            self.ogeemag,
            self.ogeephase))


class LighthouseBsCalibration:
    """Container for calibration data of one Lighthouse base station"""

    SIZE_FLOAT = 4
    SIZE_BOOL = 1
    SIZE_SWEEP = 7 * SIZE_FLOAT
    SIZE_CALIBRATION = 2 * SIZE_SWEEP + SIZE_BOOL

    def __init__(self):
        self.sweeps = [LighthouseCalibrationSweep(),
                       LighthouseCalibrationSweep()]
        self.valid = True

    def set_from_mem_data(self, data):
        self.sweeps[0] = self._unpack_sweep_calibration(
            data[0:self.SIZE_SWEEP])
        self.sweeps[1] = self._unpack_sweep_calibration(
            data[self.SIZE_SWEEP:self.SIZE_SWEEP * 2])
        self.valid = struct.unpack('<?', data[self.SIZE_SWEEP * 2:])[0]

    def _unpack_sweep_calibration(self, data):
        result = LighthouseCalibrationSweep()

        (result.phase,
         result.tilt,
         result.curve,
         result.gibmag,
         result.gibphase,
         result.ogeemag,
         result.ogeephase) = struct.unpack('<fffffff', data)

        return result

    def add_mem_data(self, data):
        self._pack_sweep_calib(data, self.sweeps[0])
        self._pack_sweep_calib(data, self.sweeps[1])
        data += struct.pack('<?', self.valid)

    def _pack_sweep_calib(self, data, sweep_calib):
        data += struct.pack('<fffffff',
                            sweep_calib.phase,
                            sweep_calib.tilt,
                            sweep_calib.curve,
                            sweep_calib.gibmag,
                            sweep_calib.gibphase,
                            sweep_calib.ogeemag,
                            sweep_calib.ogeephase)

    def dump(self):
        self.sweeps[0].dump()
        self.sweeps[1].dump()
        print('valid: {}'.format(self.valid))


class LighthouseMemory(MemoryElement):
    """
    Memory interface for lighthouse configuration data
    """
    GEO_START_ADDR = 0x00
    CALIB_START_ADDR = 0x1000
    PAGE_SIZE = 0x100
    NUMBER_OF_BASESTATIONS = 2
    SIZE_GEOMETRY_ALL = NUMBER_OF_BASESTATIONS * \
        LighthouseBsGeometry.SIZE_GEOMETRY

    def __init__(self, id, type, size, mem_handler):
        """Initialize Lighthouse memory"""
        super(LighthouseMemory, self).__init__(id=id, type=type, size=size,
                                               mem_handler=mem_handler)

        self._clear_update_cb()
        self._clear_write_cb()

    def new_data(self, mem, addr, data):
        """Callback for when new memory data has been fetched"""
        if mem.id == self.id:
            tmp_update_finished_cb = self._update_finished_cb
            self._clear_update_cb()

            if addr < self.CALIB_START_ADDR:
                geo_data = LighthouseBsGeometry()
                geo_data.set_from_mem_data(data)

                if tmp_update_finished_cb:
                    tmp_update_finished_cb(self, geo_data)
            else:
                calibration_data = LighthouseBsCalibration()
                calibration_data.set_from_mem_data(data)

                if tmp_update_finished_cb:
                    tmp_update_finished_cb(self, calibration_data)

    def new_data_failed(self, mem, addr, data):
        """Callback when a read failed"""
        if mem.id == self.id:
            tmp_update_failed_cb = self._update_failed_cb
            self._clear_update_cb()

            if tmp_update_failed_cb:
                logger.debug('Update of data failed')
                tmp_update_failed_cb(self)

    def read_geo_data(self, bs_id, update_finished_cb, update_failed_cb=None):
        """Request a read of geometry data for one base station"""
        if self._update_finished_cb:
            raise Exception('Read operation already ongoing')
        self._update_finished_cb = update_finished_cb
        self._update_failed_cb = update_failed_cb
        self.mem_handler.read(self, self.GEO_START_ADDR + bs_id *
                              self.PAGE_SIZE,
                              LighthouseBsGeometry.SIZE_GEOMETRY)

    def read_calib_data(self, bs_id, update_finished_cb,
                        update_failed_cb=None):
        """Request a read of calibration data for one base station"""
        if self._update_finished_cb:
            raise Exception('Read operation already ongoing')
        self._update_finished_cb = update_finished_cb
        self._update_failed_cb = update_failed_cb
        self.mem_handler.read(self, self.CALIB_START_ADDR + bs_id *
                              self.PAGE_SIZE,
                              LighthouseBsCalibration.SIZE_CALIBRATION)

    def write_geo_data(self, bs_id, geo_data, write_finished_cb,
                       write_failed_cb=None):
        """Write geometry data for one base station to the Crazyflie"""
        if self._write_finished_cb:
            raise Exception('Write operation already ongoing.')
        data = bytearray()
        geo_data.add_mem_data(data)
        self._write_finished_cb = write_finished_cb
        self._write_failed_cb = write_failed_cb
        geo_addr = self.GEO_START_ADDR + bs_id * self.PAGE_SIZE
        self.mem_handler.write(self, geo_addr, data, flush_queue=True)

    def write_calib_data(self, bs_id, calibration_data, write_finished_cb,
                         write_failed_cb=None):
        """Write calibration data for one basestation to the Crazyflie"""
        if self._write_finished_cb:
            raise Exception('Write operation already ongoing.')
        data = bytearray()
        calibration_data.add_mem_data(data)
        self._write_finished_cb = write_finished_cb
        self._write_failed_cb = write_failed_cb
        calib_addr = self.CALIB_START_ADDR + bs_id * self.PAGE_SIZE
        self.mem_handler.write(self, calib_addr, data, flush_queue=True)

    def _write_data_list(self, addr, data_list):
        data = bytearray()
        for bs in data_list:
            bs.add_mem_data(data)
        self.mem_handler.write(self, addr, data, flush_queue=True)

    def write_done(self, mem, addr):
        if mem.id == self.id:
            if self._write_finished_cb:
                self._write_finished_cb(self, addr)
            self._clear_write_cb()

    def write_failed(self, mem, addr):
        if mem.id == self.id:
            if self._write_failed_cb:
                logger.debug('Write of data failed')
                self._write_failed_cb(self, addr)
            self._clear_write_cb()

    def disconnect(self):
        self._clear_update_cb()
        self._clear_write_cb()

    def _clear_update_cb(self):
        self._update_finished_cb = None
        self._update_failed_cb = None

    def _clear_write_cb(self):
        self._write_finished_cb = None
        self._write_failed_cb = None


class LighthouseMemHelper:
    """Helper to access all geometry data located in crazyflie memory subsystem"""

    NR_OF_CHANNELS = 16

    def __init__(self, cf):
        self._cf = cf

        self._result_geos = None
        self._next_geo_get_id = None
        self._read_geos_done_cb = None

        self._geos_to_write = None
        self._write_done_cb = None
        self._write_failed_for_one_or_more_geos = False

        mems = self._cf.mem.get_mems(MemoryElement.TYPE_LH)
        count = len(mems)
        if count != 1:
            raise Exception('Unexpected nr of memories found:', count)

        self._lh_mem = mems[0]

    def read_all_geos(self, read_done_cb):
        if self._read_geos_done_cb is not None:
            raise Exception('Read operation not finished')

        self._result_geos = {}
        self._next_geo_get_id = 0
        self._read_geos_done_cb = read_done_cb
        self._get_geo(0)

    def write_geos(self, geometry_dict, write_done_cb):
        if self._geos_to_write is not None:
            raise Exception('Write operation not finished')

        self._write_done_cb = write_done_cb
        # Make a copy of the dictionary
        self._geos_to_write = dict(geometry_dict)
        self._write_failed_for_one_or_more_geos = False
        self._write_next_geo()

    def _write_next_geo(self):
        if len(self._geos_to_write) > 0:
            id = list(self._geos_to_write.keys())[0]
            geo_data = self._geos_to_write.pop(id)
            self._lh_mem.write_geo_data(id, geo_data, self._geo_data_written, write_failed_cb=self._write_failed)
        else:
            tmp_cb = self._write_done_cb
            is_sucess = not self._write_failed_for_one_or_more_geos

            self._geos_to_write = None
            self._write_done_cb = None

            tmp_cb(is_sucess)

    def _geo_data_updated(self, mem, geo_data):
        self._result_geos[self._next_geo_get_id] = geo_data
        self._next_geo_get_id += 1
        self._get_geo(self._next_geo_get_id)

    def _update_failed(self, mem):
        # Update failes if the geo is not available, that is if we try to read a base station id that is
        # not supported by the firmware. Try to read the next one until we're done.
        self._next_geo_get_id += 1
        self._get_geo(self._next_geo_get_id)

    def _get_geo(self, channel):
        if channel < self.NR_OF_CHANNELS:
            self._lh_mem.read_geo_data(channel, self._geo_data_updated, update_failed_cb=self._update_failed)
        else:
            tmp_cb = self._read_geos_done_cb
            tmp_result = self._result_geos

            self._read_geos_done_cb = None
            self._result_geos = None
            self._next_geo_get_id = None
            self._write_failed_for_one_or_more_geos = False

            tmp_cb(tmp_result)

    def _geo_data_written(self, mem, addr):
        self._write_next_geo()

    def _write_failed(self, mem, addr):
        # Write failes if we try to write data for a base station that is not supported by the fw.
        # Try to write the next one until we have tried them all, but record the problem and
        # report that not all base stations were written.
        self._write_failed_for_one_or_more_geos = True
        self._write_next_geo()
