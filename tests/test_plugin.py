import pytest


@pytest.mark.order("first")
def test_plugin_can_be_found(registry):
    assert registry.GetPluginWithName("usdFbx") is not None


# Marking as one of the first tests as to prevent tests implicitely loading the plugin running before this
# This depends on the pytest-order plugin to be installed!
@pytest.mark.order("second")
def test_is_plugin_loadable(registry):
    plugin = registry.GetPluginWithName("usdFbx")
    assert not plugin.isLoaded
    plugin.Load()
    assert plugin.isLoaded
