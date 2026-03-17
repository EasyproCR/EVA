from guardrails import Guard

def build_Select_Guard() -> Guard:
    rail = r"""
<rail version="0.1">
  <o>
    <string name="response"
      format="regex:^(?!.*\b(insert|update|delete|drop|alter|create|truncate|replace|grant|revoke)\b).*"/>
  </o>
</rail>
"""
    return Guard.for_rail_string(rail)
    
