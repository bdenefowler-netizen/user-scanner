import anvil.server
from anvil import *

from ._anvil_designer import Form1Template

class Form1(Form1Template):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    super().__init__(**properties)

    self.mode_dropdown.items = [("Username", "username"), ("Email", "email")]
    self.mode_dropdown.selected_value = "username"
    self.results_panel.items = []
    self._refresh_categories()

  def _refresh_categories(self):
    self.results_panel.items = []
    response = anvil.server.call("get_scan_catalog", self.mode_dropdown.selected_value)
    if not response["ok"]:
      self.status_label.text = response["message"]
      self.category_dropdown.items = []
      self.module_dropdown.items = []
      return

    categories = response["categories"]
    self.category_dropdown.items = [
      (item["label"], item["value"]) for item in categories
    ]
    self.category_dropdown.selected_value = categories[0]["value"] if categories else None
    self._refresh_modules()

  def _refresh_modules(self):
    category = self.category_dropdown.selected_value
    if not category:
      self.module_dropdown.items = []
      self.module_dropdown.selected_value = None
      return

    response = anvil.server.call(
      "get_scan_catalog", self.mode_dropdown.selected_value, category
    )
    if not response["ok"]:
      self.status_label.text = response["message"]
      self.module_dropdown.items = []
      self.module_dropdown.selected_value = None
      return

    modules = response["modules"]
    self.module_dropdown.items = [
      (item["label"], item["value"]) for item in modules
    ]
    self.module_dropdown.selected_value = modules[0]["value"] if modules else None

  @handle("mode_dropdown", "change")
  def mode_dropdown_change(self, **event_args):
    self._refresh_categories()

  @handle("category_dropdown", "change")
  def category_dropdown_change(self, **event_args):
    self._refresh_modules()

  @handle("scan_button", "click")
  def scan_button_click(self, **event_args):
    target = (self.target_box.text or "").strip()
    scan_type = self.mode_dropdown.selected_value

    if not target:
      self.status_label.text = "Enter a username or email address."
      return
    if scan_type == "email" and ("@" not in target or "." not in target.rsplit("@", 1)[-1]):
      self.status_label.text = "Enter a valid email address."
      return
    if scan_type == "username" and (
      len(target) > 64
      or any(character.isspace() for character in target)
      or any(character in target for character in "/?#")
    ):
      self.status_label.text = "Enter a username up to 64 characters without spaces or / ? #."
      return
    if not self.category_dropdown.selected_value or not self.module_dropdown.selected_value:
      self.status_label.text = "Choose a category and platform."
      return

    self.scan_button.enabled = False
    self.results_panel.items = []
    self.status_label.text = "Checking the selected platform…"
    try:
      response = anvil.server.call(
        "scan_module",
        target,
        scan_type,
        self.category_dropdown.selected_value,
        self.module_dropdown.selected_value,
      )
      if not response["ok"]:
        self.status_label.text = response["message"]
        return

      results = response["results"]
      for result in results:
        extra = result.get("extra", {})
        result["extra_summary"] = ", ".join(
          "{}: {}".format(key.replace("_", " ").title(), value)
          for key, value in extra.items()
        )
      self.results_panel.items = results
      self.status_label.text = "Check complete. Results are shown below."
    finally:
      self.scan_button.enabled = True
