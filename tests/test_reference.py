"""Offline tests: no bench, network, database, service restart or paid CI required."""
import hashlib
import importlib.util
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import sys
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def load_reference():
    fake = ModuleType("frappe")
    utils = ModuleType("frappe.utils")
    utils.getdate = lambda v: v
    utils.nowdate = lambda: "2026-10-15"
    with patch.dict(sys.modules, {"frappe": fake, "frappe.utils": utils}):
        spec = importlib.util.spec_from_file_location("reference_under_test", ROOT / "mastercellar/reference.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    return module, fake


class ReferenceTests(unittest.TestCase):
    def setUp(self):
        self.mod, self.frappe = load_reference()
        self.svg = b'<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20"><path d="M0 0h10v10H0z"/></svg>'
        self.manifest = {"version":"20261015-reference-v1", "products":[{
            "item_code":"TMC-REF-ABCDEF012345", "name":"Test wine", "price":"27.25",
            "description":"Sample", "image":"photo.svg", "categories":["Maltese Wines"]}],
            "files":{"photo.svg":hashlib.sha256(self.svg).hexdigest()}, "brand":{"logo":"photo.svg"}}

    def test_money_exact(self):
        self.assertEqual(self.mod.money_cents("27.25"),2725)
    def test_rounding(self):
        self.assertEqual(self.mod.money_cents("1.005"),101)
    def test_zero_price_preserved(self):
        self.assertEqual(self.mod.money_cents(0),0)
    def test_bad_prices_rejected(self):
        for val in [None,"NaN","Infinity","-1","garbage",100001]:
            self.assertIsNone(self.mod.money_cents(val))
    def test_json_cannot_close_script(self):
        value={"name":"</script><script>alert(1)</script>&"}
        rendered=self.mod.safe_json(value)
        self.assertNotIn("<",rendered)
        self.assertEqual(json.loads(rendered),value)
    def test_bundle_accepted(self):
        self.mod.validate_bundle(self.manifest,["images/photo.svg"])
    def test_wrong_version(self):
        self.manifest["version"]="unknown"
        with self.assertRaises(ValueError):self.mod.validate_bundle(self.manifest,["images/photo.svg"])
    def test_wrong_code(self):
        self.manifest["products"][0]["item_code"]="PRODUCTION-01"
        with self.assertRaises(ValueError):self.mod.validate_bundle(self.manifest,["images/photo.svg"])
    def test_duplicate_codes(self):
        self.manifest["products"]*=2
        with self.assertRaises(ValueError):self.mod.validate_bundle(self.manifest,["images/photo.svg"])
    def test_missing_photo(self):
        with self.assertRaises(ValueError):self.mod.validate_bundle(self.manifest,[])
    def test_path_traversal(self):
        self.manifest["files"]["../bad.svg"]="0"*64
        with self.assertRaises(ValueError):self.mod.validate_bundle(self.manifest,["images/photo.svg","images/../bad.svg"])
    def test_non_image_asset(self):
        self.manifest["files"]["test.ttf"]="0"*64
        with self.assertRaises(ValueError):self.mod.validate_bundle(self.manifest,["images/photo.svg","images/test.ttf"])
    def test_invalid_category(self):
        self.manifest["products"][0]["categories"]=["Unknown"]
        with self.assertRaises(ValueError):self.mod.validate_bundle(self.manifest,["images/photo.svg"])
    def test_wrong_site_rejected(self):
        self.frappe.local=SimpleNamespace(site="grixti.local")
        self.frappe.throw=lambda msg:(_ for _ in ()).throw(ValueError(msg))
        with self.assertRaisesRegex(ValueError,"restricted"):
            self.mod.install_bundle()
    def _set_site(self,root):
        self.frappe.local=SimpleNamespace(site=self.mod.SITE)
        self.frappe.get_site_path=lambda *parts:str(Path(root).joinpath(*parts))
    def _make_zip(self,root,svg=None):
        p=Path(root)/"private/files/mastercellar-reference-assets.zip";p.parent.mkdir(parents=True,exist_ok=True)
        with zipfile.ZipFile(p,"w") as z:
            z.writestr("manifest.json",json.dumps(self.manifest))
            z.writestr("images/photo.svg",self.svg if svg is None else svg)
        return p
    def test_preview_no_db_writes(self):
        with TemporaryDirectory() as root:
            self._set_site(root);self._make_zip(root)
            result=self.mod.install_bundle()
            self.assertTrue(result["dry_run"])
            self.assertEqual(result["reference_products"],1)
            self.assertEqual(result["created_items"],0)
            self.assertFalse((Path(root)/"private/mastercellar-reference.json").exists())
    def test_installer_rejects_path(self):
        with TemporaryDirectory() as root:
            self._set_site(root)
            with self.assertRaises(ValueError):self.mod.install_bundle(file_name="../bad.zip")
    def test_installer_rejects_non_boolean(self):
        with TemporaryDirectory() as root:
            self._set_site(root)
            with self.assertRaises(ValueError):self.mod.install_bundle(dry_run="False")
    def test_hash_mismatch_rejected(self):
        with TemporaryDirectory() as root:
            self._set_site(root);self._make_zip(root,svg=b"bad")
            with self.assertRaisesRegex(ValueError,"hash"):
                self.mod.install_bundle()
    def test_svg_script_rejected(self):
        with TemporaryDirectory() as root:
            self._set_site(root)
            self.svg=b'<svg><script>alert(1)</script></svg>'
            self.manifest["files"]["photo.svg"]=hashlib.sha256(self.svg).hexdigest()
            self._make_zip(root)
            with self.assertRaisesRegex(ValueError,"SVG"):
                self.mod.install_bundle()
    def test_install_then_repeat_preserves_items_and_prices(self):
        with TemporaryDirectory() as root:
            self._set_site(root);self._make_zip(root)
            records={
                ("Item Group","All Item Groups"):{"name":"All Item Groups"},
                ("UOM","Nos"):{"name":"Nos"},
            }
            def exists(doctype, value):
                if isinstance(value,str):return (doctype,value) in records
                return any(dt==doctype and all(d.get(k)==v for k,v in value.items())
                           for (dt,_),d in records.items())
            def doc(data):
                class Doc:
                    def insert(self,**kwargs):
                        name=(data.get("item_code") if data["doctype"]=="Item" else
                              data.get("item_group_name") or data.get("price_list_name") or str(len(records)))
                        records[data["doctype"],name]=dict(data)
                        return self
                return Doc()
            self.frappe.get_doc=doc
            self.frappe.db=SimpleNamespace(exists=exists,commit=lambda:None,
                get_value=lambda dt,name,field:records[dt,name].get(field))
            manager=ModuleType("frappe.utils.file_manager")
            def save_file(name,payload,*args,**kwargs):
                url="/files/"+name
                records["File",name]={"file_url":url,"is_private":0}
                return SimpleNamespace(file_url=url)
            manager.save_file=save_file
            with patch.dict(sys.modules,{"frappe.utils.file_manager":manager}):
                first=self.mod.install_bundle(dry_run=False)
                self.assertEqual(first["created_items"],1)
                self.assertEqual(first["created_prices"],1)
                item=records["Item","TMC-REF-ABCDEF012345"]
                item["item_name"]="User-edited name"
                snapshot=dict(records)
                second=self.mod.install_bundle(dry_run=False)
                self.assertEqual(second["created_items"],0)
                self.assertEqual(second["created_prices"],0)
                self.assertEqual(records,snapshot)
                self.assertEqual(item["item_name"],"User-edited name")

    def test_empty_payload_before_install(self):
        with TemporaryDirectory() as root:
            self._set_site(root)
            self.assertFalse(self.mod.get_payload()["ready"])
            self.assertEqual(self.mod.get_payload()["products"],[])
    def test_no_web_write_endpoints(self):
        source=(ROOT/"mastercellar/reference.py").read_text()
        self.assertNotIn("@frappe.whitelist",source)
        self.assertNotIn('"Sales Order"',source)
        self.assertNotIn('"Payment Entry"',source)
    def test_browser_has_no_external_submission(self):
        js=(ROOT/"mastercellar/public/js/reference.js").read_text()
        for term in ["fetch(","XMLHttpRequest", "sendBeacon", "frappe.call", "/api/method/"]:
            self.assertNotIn(term,js)
        self.assertIn("sessionStorage",js)
        self.assertIn("Place order — demo only",js)

if __name__ == "__main__":
    unittest.main()
