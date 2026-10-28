import importlib.util
import sys
import unittest
from pathlib import Path

P=Path(__file__).resolve().parents[1]/"scripts"/"compose_messages.py"
S=importlib.util.spec_from_file_location("compose_messages",P); M=importlib.util.module_from_spec(S); sys.modules["compose_messages"]=M; S.loader.exec_module(M)

class Tests(unittest.TestCase):
    def test_route_kind(self):
        self.assertEqual(M.route_kind("https://x.com/advertise"),"commercial")
        self.assertEqual(M.route_kind("https://x.com/write-for-us"),"editorial")
        self.assertEqual(M.route_kind("https://x.com/contact"),"routing")

    def test_large_batch_has_structural_variation(self):
        rows=[]
        for i in range(40):
            rows.append({"site_name":f"Publisher {i}","industry":"Industrial construction","content_angle":f"steel facility topic {i}","contact_info":{"recommended_url":"https://publisher.example/advertise"}})
        bodies=[M.body_for(row,i,"commercial","Sample Sender") for i,row in enumerate(rows)]
        normalized=[M.normalize_copy(body) for body in bodies]
        from difflib import SequenceMatcher
        maximum=max(SequenceMatcher(None,left,right).ratio() for i,left in enumerate(normalized) for right in normalized[i+1:])
        self.assertLess(maximum,0.9)

if __name__=="__main__": unittest.main()
