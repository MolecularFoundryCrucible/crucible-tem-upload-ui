"""
Instrument-specific file parsers for the multi-assignment upload UI.

To add a new instrument:
  1. Write a parser function: (path: str) -> list[dict]
     Each dict must have keys: position (str), name (str), uuid (str), excluded (bool)
  2. Register it in FILE_PARSERS keyed by instrument name.
  3. Set the instrument's UI mode in instrument_conf.py:
     INSTRUMENT_UI_MODE = {'your_instrument': 'multi_assignment', ...}
"""

import h5py


def _parse_nirvana_h5(path: str) -> list[dict]:
    """Extract sample names and UUIDs from a Nirvana ScopeFoundry h5 file.

    Samples are stored as HDF5 attributes on position groups under
    /measurement/{name}/positions/pos_NNN_<samplename>/.
    """
    def decode(v):
        return v.decode() if isinstance(v, (bytes, bytearray)) else str(v)

    samples = []
    with h5py.File(path, 'r') as f:
        meas_grp = f.get('measurement')
        if meas_grp is None:
            raise ValueError("No /measurement group found in this file")
        meas_name = next(iter(meas_grp.keys()))
        positions = meas_grp[meas_name].get('positions')
        if positions is None:
            raise ValueError(f"No positions group found under /measurement/{meas_name}")
        for i, pos_name in enumerate(sorted(positions.keys())):
            attrs = positions[pos_name].attrs
            sample_name = decode(attrs['sample_name']) if 'sample_name' in attrs else pos_name
            sample_uuid = decode(attrs['sample_uuid']) if 'sample_uuid' in attrs else ''
            samples.append({
                'position': f'S{i+1:02d}',
                'name': sample_name,
                'uuid': sample_uuid,
                'excluded': False,
            })
    return samples


# Registry: instrument_name -> parser callable
FILE_PARSERS = {
    'nirvana': _parse_nirvana_h5,
}
