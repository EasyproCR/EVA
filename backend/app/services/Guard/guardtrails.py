from guardrails import Guard

def build_Select_Guard(guard: Guard) -> Guard:
    rail = r"""
<rail version="0.1">
  <output>
    <string name="response"
      format="regex:^(?!.*\b(insert|update|delete|drop|alter|create|truncate|replace|grant|revoke)\b).*"/>
  </output>
</rail>
"""
    return guard.for_rail_string(rail)
