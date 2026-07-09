import os
HOME = os.environ.get('HOME')

DEFAULT_BROWSE_DIR = '/home/timko/Documents'
# True  = pick a folder; create parent session dataset + one child dataset per file inside
# False = pick one or more files; each becomes its own standalone dataset (or insitu, per instrument)
IS_SESSION = False
INSTRUMENTS = ['titanx', 'themis', 'team1', 'team05', 'spectre', 'insitu_pl', 'spinbot', 'nirvana']
DEFAULT_INSTRUMENT_NAME = 'nirvana'

# Maps session-mode instruments to their Prefect deployment (flow-name/deployment-name).
# Only consulted in session mode (IS_SESSION = True); non-session uploads always use
# the generic upload-dataset / multi-file-upload deployments.
INSTRUMENT_FLOWS = {
    'titanx': 'session-upload/session-upload',
}

# Post-processing requested on each dataset after its files land, keyed by instrument.
# Each name maps to client.datasets.request_<name> (e.g. "insitu_aggregation" ->
# request_insitu_aggregation). Instruments not listed get no post-processing.
POST_PROCESSING_REQUESTS = {
    'insitu_pl': ['insitu_aggregation'],
}
# True  = run an instrument's post-processing requests sequentially; each depends on
#         the previous succeeding (a failure halts the rest).
# False = request all of them in parallel (independent of each other).
CHAIN_POST_PROCESSING = True

# Maps instrument name to UI mode.
# 'multi_assignment' — replaces the single-sample lookup with a per-file
#                      sample assignment grid (requires a FILE_PARSERS entry
#                      in instrument_plugins.py for that instrument).
# Instruments not listed use the default single-sample lookup UI.
AVAILABLE_INGESTORS = [
    'AFMIngestor',
    'PtychographyH5Ingestor',
    'SimpleTiledImageScopeFoundryH5Ingestor',
    'BioGlowIngestor',
    'QSpleemSVRampIngestor',
    'QSpleemSVRampSpinIngestor',
    'QSpleemImageIngestor',
    'QSpleemSPLEEMImageIngestor',
    'QSpleemDepositionMonitorIngestor',
    'QSpleemARRESEKIngestor',
    'QSpleemARRESMMIngestor',
    'RgaTeyBatchIngestor',
    'CanonCaptureScopeFoundryH5Ingestor',
    'SingleSpecScopeFoundryH5Ingestor',
    'HyperspecScopeFoundryH5Ingestor',
    'HyperspecSweepScopeFoundryH5Ingestor',
    'ToupcamLiveScopeFoundryH5Ingestor',
    'CLSyncRasterScanIngestor',
    'CLHyperspecIngestor',
    'SpinbotSpecLineIngestor',
    'SpinbotCameraCaptureIngestor',
    'SpinbotPhotoRunIngestor',
    'InSituPlIngestor',
    'CziIngestor',
    'DigitalMicrographIngestor',
    'EmiIngestor',
    'SerIngestor',
    'BcfIngestor',
    'BerkeleyEmdIngestor',
    'VeloxEmdIngestor',
    'SpinbotSpecRunIngestor',
    'ImageIngestor',
    'NirvanaMultiPosLineScanIngestor',
    'ScopeFoundryH5Ingestor',
    'H5Ingestor',
]

# Default ingestor per instrument. Must be a value from AVAILABLE_INGESTORS or ''.
# Leave an instrument out (or set to '') to use Crucible's server-side default.
INSTRUMENT_INGESTORS = {
    'nirvana': 'NirvanaMultiPosLineScanIngestor',
}

INSTRUMENT_UI_MODE = {
    'nirvana': 'multi_assignment',
}

# Per-instrument holder layout for the "From holders" data source in multi_assignment mode.
# Each entry is a list of holders in display order; 'slots' is the expected number of
# child samples per holder.  When Crucible gains a layout metadata field on holder samples
# these values become the fallback — the API response takes precedence.
INSTRUMENT_HOLDER_LAYOUT = {
    'nirvana': [
        {'label': 'Tray A', 'slots': 8},
        {'label': 'Tray B', 'slots': 8},
    ],
}

# For instruments in multi_assignment mode:
# False (default) — one file → one Crucible dataset linked to all checked sample UUIDs
# True            — one file → one Crucible dataset per sample (each linked to one UUID)
MULTI_ASSIGNMENT_ONE_PER_SAMPLE = False

PRINT_BARCODE_ENABLED = False
ACCEPTABLE_FILE_TYPES = {'.bcf', '.dm3', '.dm4', '.emd', '.h5', '.mcr', '.ser', '.txt'}

'''
To enable barcode printing: 
- set PRINT_BARCODE_ENABLED to True
- Connect a brother pt-d610bt label printer to the computer running this code, and set the printer name in the print_label function in backend.py
- Install the required libraries: uv add pywin32
- Install printer driver from here: https://support.brother.com/g/b/downloadtop.aspx?c=us&lang=en&prod=d610bteus
- Find the printer in settings under printers and scanners and note the exact name (e.g. "Brother PT-D610BT")
- Download the brothers SDK for Windows B-pac (made a free account)
- Set printer settings through windows to match the tape type and size that you want to print (https://docs.google.com/presentation/d/1vSS1Xp0fzIwflpj50vx5LOO9MuW7FtZhLS1EQ7D4opI/edit?usp=sharing)
'''

