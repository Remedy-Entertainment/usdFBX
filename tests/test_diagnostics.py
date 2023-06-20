import pytest
from pxr import Tf, Usd


@pytest.fixture(
    params=[
        ("USDFBX", "UsdFbx"),
        ("USDFBX_FBX_READERS", "UsdFbx::FbxReaders"),
    ],
    scope="function",
)
def debug_symbols(request, registry):
    # We kind of "force" plugin loading here as otherwise the DebugSymbols are unknown
    # This is not an issue when running the entire test suite, but can be problematic
    # when running test_diagnostics by itself.
    # pytest.mark.order(after="othermodule.py::test") does not seem to work very well if you run in isolation too
    plugin = registry.GetPluginWithName("usdFbx")
    if not plugin.isLoaded:
        plugin.Load()
    symbol, expected = request.param
    Tf.Debug.SetDebugSymbolsByName(symbol, 1)
    yield symbol, expected
    Tf.Debug.SetDebugSymbolsByName(symbol, 0)

# TODO: There are some inconsistent results when testing this in Debug builds...
# [NL-29071]
def test_debug_symbol(basic_plane_fbx, debug_symbols, capfd):
    symbol, expected = debug_symbols
    mesh_file_path = basic_plane_fbx[0]
    _ = Usd.Stage.Open(str(mesh_file_path))
    assert Tf.Debug.IsDebugSymbolNameEnabled(symbol)
    out, _ = capfd.readouterr()
    lines = [l for l in out.splitlines() if l.startswith(expected)]
    assert lines


def test_debug_symbols_exist(debug_symbols):
    debugCodes = Tf.Debug.GetDebugSymbolNames()
    assert debug_symbols[0] in debugCodes
