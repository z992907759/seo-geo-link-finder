import importlib.util, sys, unittest
from pathlib import Path
P=Path(__file__).resolve().parents[1]/"scripts"/"contact_discovery.py"
S=importlib.util.spec_from_file_location("contact_discovery",P); M=importlib.util.module_from_spec(S); sys.modules["contact_discovery"]=M; S.loader.exec_module(M)
class Tests(unittest.TestCase):
    def test_page_kind(self):
        self.assertEqual(M.page_kind("https://x.com/write-for-us/",""),"submission")
        self.assertEqual(M.page_kind("https://x.com/advertise/",""),"advertising")
    def test_recipient_fit_gate(self):
        aligned={"https://x.com/contact/","https://x.com/advertise/"}
        self.assertEqual(M.assess_recipient_fit("editor@x.com","https://x.com/",aligned)[0],"high")
        self.assertEqual(M.assess_recipient_fit("info@x.com","https://x.com/contact/",aligned)[0],"medium")
        self.assertEqual(M.assess_recipient_fit("events@x.com","https://x.com/contact/",aligned)[0],"reject")
        self.assertEqual(M.assess_recipient_fit("jane@x.com","https://x.com/",aligned)[0],"reject")

    def test_wrong_departments_are_rejected(self):
        aligned={"https://x.com/advertise/"}
        for email in ("hr@x.com", "legal@x.com", "admissions@x.com", "circulation@x.com", "support@x.com", "press@x.com"):
            self.assertEqual(M.assess_recipient_fit(email,"https://x.com/advertise/",aligned)[0],"reject")

    def test_general_inbox_requires_cooperation_page(self):
        self.assertEqual(M.assess_recipient_fit("info@x.com","https://x.com/contact/",set())[0],"reject")
        self.assertEqual(M.assess_recipient_fit("info@x.com","https://x.com/advertise/",{"https://x.com/advertise/"})[0],"medium")
if __name__=="__main__": unittest.main()
