"""
This module documents the orchestration "graph" in code form, even though
we run a custom loop instead of a graph-execution library.

    START
      |
      v
    load_projects()                      [tools/data_loader.py]
      |
      v
    CoordinatorAgent.run_review()        [agents/coordinator_agent.py]
      |
      +--> FinanceAgent.run()   --> AgentReport
      +--> DeliveryAgent.run()  --> AgentReport
      +--> EquityAgent.run()    --> AgentReport
      |
      v
    rank_funding_candidates()            [tools/ranking_tools.py]
      |
      v
    select_within_budget()               [tools/ranking_tools.py]
      |
      v
    _detect_conflicts()                  [agents/coordinator_agent.py]
      |
      v
    FinalReport                          [models/messages.py]
      |
      v
    STOP

See agents/coordinator_agent.py::CoordinatorAgent.run_review for the actual
executable implementation of this flow, and agents/base_agent.py for the
per-agent PLAN -> ACT -> OBSERVE -> REASON loop each specialist runs
internally before returning its AgentReport to the Coordinator.
"""
