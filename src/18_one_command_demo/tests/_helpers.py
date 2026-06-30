import json
import os
import tempfile
import unittest

from one_command_demo_lib import versions


class WrapperCase(unittest.TestCase):
    def make_config(self, with_demo_py=True):
        tmp = tempfile.mkdtemp(prefix="ocd_test_")
        root = os.path.join(tmp, "connected_demo_v01")
        os.makedirs(root, exist_ok=True)
        if with_demo_py:
            with open(os.path.join(root, "connected_demo.py"), "w") as h:
                h.write("# placeholder\n")
        demo_cfg = os.path.join(tmp, "connected_demo_config.json")
        with open(demo_cfg, "w") as h:
            json.dump({}, h)
        cfg = os.path.join(tmp, "wrapper_config.json")
        with open(cfg, "w") as h:
            json.dump({"config_version": versions.CONFIG_VERSION,
                       "connected_demo_root": root,
                       "connected_demo_config": demo_cfg}, h)
        return tmp, cfg, root

    def out_dir(self, tmp, name="out"):
        return os.path.join(tmp, name)
