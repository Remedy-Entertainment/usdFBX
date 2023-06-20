import uuid
from pxr import Usd
import FbxCommon as fbx


def validate_property_animation(stage, prop, expected_start_end_values):
    start_time, end_time = stage.GetStartTimeCode(), stage.GetEndTimeCode()
    assert prop.GetNumTimeSamples() == end_time - start_time + 1
    time_samples = prop.GetTimeSamples()
    assert time_samples[0] == start_time
    assert time_samples[-1] == end_time

    expected_start_value, expected_end_value = expected_start_end_values

    assert prop.Get(Usd.TimeCode(time_samples[0])) == expected_start_value
    assert prop.Get(Usd.TimeCode(time_samples[-1])) == expected_end_value


def validate_stage_time_metrics(stage, expected_usd_times):
    start_time, end_time = stage.GetStartTimeCode(), stage.GetEndTimeCode()
    expected_start_time, expected_end_time = expected_usd_times
    if expected_usd_times[1] < expected_usd_times[0]:
        expected_start_time, expected_end_time = (
            expected_usd_times[1],
            expected_usd_times[0],
        )
    assert Usd.TimeCode(start_time) == expected_start_time
    assert Usd.TimeCode(end_time) == expected_end_time

    return expected_usd_times[1] < expected_usd_times[0]


def create_FbxTime(frames):
    """
    Create an fbxtime with a specific framecount
    Its default constructor does not handle it
    """
    time = fbx.FbxTime()
    time.SetFrame(frames)
    return time
