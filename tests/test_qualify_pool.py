import importlib.util
import sys
import unittest
from pathlib import Path

P=Path(__file__).resolve().parents[1]/"scripts"/"qualify_pool.py"
S=importlib.util.spec_from_file_location("qualify_pool",P); M=importlib.util.module_from_spec(S); sys.modules["qualify_pool"]=M; S.loader.exec_module(M)

class Tests(unittest.TestCase):
    def test_gates(self):
        good={"domain":"publisher.com","quality_checks":{"traffic_estimate":1200}}
        low={"domain":"publisher.com","quality_checks":{"traffic_estimate":999}}
        platform={"domain":"sciencedirect.com","quality_checks":{"traffic_estimate":100000}}
        self.assertTrue(M.qualify(good,1000)[0])
        self.assertFalse(M.qualify(low,1000)[0])
        self.assertFalse(M.qualify(platform,1000)[0])

if __name__=="__main__": unittest.main()
