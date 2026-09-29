from ._anvil_designer import ResultRowTemplate


class ResultRow(ResultRowTemplate):
  def __init__(self, **properties):
    super().__init__(**properties)
