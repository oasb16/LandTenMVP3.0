# Example JSON Responses - AI Reasoning V2

**Purpose:** Reference document showing expected JSON responses for each workflow stage

This document provides example responses from the AI reasoning engine for different stages and scenarios. Use these for testing and validation.

---

## Table of Contents

1. [Idle Stage](#idle-stage)
2. [Discovery Stage](#discovery-stage)
3. [Job-Ready Stage](#job-ready-stage)
4. [Approval Pending Stage](#approval-pending-stage)
5. [Job Stage](#job-stage)
6. [Error Scenarios](#error-scenarios)

---

## Idle Stage

### Scenario 1: New Incident Report

**Input:**
```json
{
  "message": "There's water leaking in my kitchen",
  "context": {
    "flow_state": {
      "stage": "idle"
    },
    "active_incident_id": null,
    "persona": "tenant"
  }
}
```

**Output (from `ai_reasoning.post_process_reasoning()`):**
```json
{
  "intent": "incident.report",
  "summary": "Plumbing issue reported",
  "reply": "I've detected an issue. Let me help you create an incident report.",
  "entities": {
    "category": "plumbing",
    "severity": "medium",
    "location": "kitchen"
  },
  "actions": ["create_incident"],
  "persona": "tenant",
  "reasoning": {
    "raw_intent": "incident.report",
    "final_intent": "incident.report",
    "stage": "idle",
    "layers_applied": [
      {
        "layer": "flow_state_override",
        "override_reason": "No override needed",
        "applied": false
      },
      {
        "layer": "safety_guard",
        "override_reason": "No safety override needed",
        "applied": false
      },
      {
        "layer": "short_message_resolver",
        "override_reason": "Not a short message",
        "applied": false
      }
    ],
    "confidence": 0.9
  }
}
```

### Scenario 2: Greeting

**Input:**
```json
{
  "message": "Hello",
  "context": {
    "flow_state": {
      "stage": "idle"
    },
    "persona": "tenant"
  }
}
```

**Output:**
```json
{
  "intent": "greeting",
  "summary": "Hello",
  "reply": "Hello! I'm your PropertyAI assistant. How can I help you today?",
  "entities": {},
  "actions": [],
  "persona": "tenant",
  "reasoning": {
    "raw_intent": "greeting",
    "final_intent": "greeting",
    "stage": "idle",
    "layers_applied": [
      {
        "layer": "flow_state_override",
        "override_reason": "No override needed",
        "applied": false
      },
      {
        "layer": "safety_guard",
        "override_reason": "No safety override needed",
        "applied": false
      },
      {
        "layer": "short_message_resolver",
        "override_reason": "Not a short message",
        "applied": false
      }
    ],
    "confidence": 0.8
  }
}
```

---

## Discovery Stage

### Scenario 1: Short Affirmative Answer ("yes")

**Input:**
```json
{
  "message": "yes",
  "context": {
    "flow_state": {
      "stage": "discovery",
      "question_index": 0,
      "last_ai_prompt": "Is the water still flowing right now?",
      "answers": {}
    },
    "active_incident_id": "INC-123",
    "persona": "tenant"
  }
}
```

**Output:**
```json
{
  "intent": "discovery.response",
  "summary": "Discovery question answered",
  "reply": "Thanks for that information. I'm recording your response.",
  "entities": {},
  "actions": ["continue_discovery"],
  "persona": "tenant",
  "reasoning": {
    "raw_intent": "general.chat",
    "final_intent": "discovery.response",
    "stage": "discovery",
    "layers_applied": [
      {
        "layer": "flow_state_override",
        "override_reason": "Intent 'general.chat' not allowed in stage 'discovery', using default 'discovery.response'",
        "applied": true
      },
      {
        "layer": "safety_guard",
        "override_reason": "No safety override needed",
        "applied": false
      },
      {
        "layer": "short_message_resolver",
        "override_reason": "Not a short message",
        "applied": false
      }
    ],
    "confidence": 0.7
  }
}
```

**Key Points:**
- Raw intent is `general.chat` (OpenAI misclassified "yes")
- Layer 2 (flow_state_override) forces `discovery.response`
- Stage remains `discovery`
- Response acknowledges answer without generic fallback

### Scenario 2: Descriptive Answer

**Input:**
```json
{
  "message": "It's leaking from under the sink in the kitchen",
  "context": {
    "flow_state": {
      "stage": "discovery",
      "question_index": 1,
      "last_ai_prompt": "Where exactly is the issue located?",
      "answers": {"q0": "yes"}
    },
    "active_incident_id": "INC-123",
    "persona": "tenant"
  }
}
```

**Output:**
```json
{
  "intent": "discovery.response",
  "summary": "Discovery question answered",
  "reply": "Thanks for that information. I'm recording your response.",
  "entities": {
    "location": "kitchen",
    "category": "plumbing"
  },
  "actions": ["continue_discovery"],
  "persona": "tenant",
  "reasoning": {
    "raw_intent": "discovery.response",
    "final_intent": "discovery.response",
    "stage": "discovery",
    "layers_applied": [
      {
        "layer": "flow_state_override",
        "override_reason": "No override needed",
        "applied": false
      },
      {
        "layer": "safety_guard",
        "override_reason": "No safety override needed",
        "applied": false
      },
      {
        "layer": "short_message_resolver",
        "override_reason": "Not a short message",
        "applied": false
      }
    ],
    "confidence": 0.9
  }
}
```

### Scenario 3: Blocked Incident Report During Discovery

**Input:**
```json
{
  "message": "There's also a problem with the electrical outlet",
  "context": {
    "flow_state": {
      "stage": "discovery",
      "question_index": 2
    },
    "active_incident_id": "INC-123",
    "persona": "tenant"
  }
}
```

**Output:**
```json
{
  "intent": "incident.followup",
  "summary": "Discovery question answered",
  "reply": "Thanks for that information. I'm recording your response.",
  "entities": {
    "category": "electrical"
  },
  "actions": ["continue_discovery"],
  "persona": "tenant",
  "reasoning": {
    "raw_intent": "incident.report",
    "final_intent": "incident.followup",
    "stage": "discovery",
    "layers_applied": [
      {
        "layer": "flow_state_override",
        "override_reason": "Intent 'incident.report' blocked in stage 'discovery', using default 'discovery.response'",
        "applied": true
      },
      {
        "layer": "safety_guard",
        "override_reason": "Cannot create new incident - active incident INC-123 exists",
        "applied": true
      },
      {
        "layer": "short_message_resolver",
        "override_reason": "Not a short message",
        "applied": false
      }
    ],
    "confidence": 0.8
  }
}
```

**Key Points:**
- Raw intent is `incident.report` (OpenAI detected incident keywords)
- Layer 2 blocks it (not allowed in discovery stage)
- Layer 3 converts to `incident.followup` (safety guard prevents new incident)
- System treats it as additional discovery information

---

## Job-Ready Stage

### Scenario 1: Affirmative Response ("yes")

**Input:**
```json
{
  "message": "yes",
  "context": {
    "flow_state": {
      "stage": "job-ready",
      "question_index": 4,
      "last_ai_prompt": "Should I create a work order now?",
      "answers": {"q0": "yes", "q1": "kitchen", "q2": "30 min ago", "q3": "no"}
    },
    "active_incident_id": "INC-123",
    "persona": "tenant"
  }
}
```

**Output:**
```json
{
  "intent": "job.request",
  "summary": "Work order requested",
  "reply": "Perfect. I'll move ahead with creating a work order.",
  "entities": {},
  "actions": ["create_job"],
  "persona": "tenant",
  "reasoning": {
    "raw_intent": "general.chat",
    "final_intent": "job.request",
    "stage": "job-ready",
    "layers_applied": [
      {
        "layer": "flow_state_override",
        "override_reason": "No override needed",
        "applied": false
      },
      {
        "layer": "safety_guard",
        "override_reason": "No safety override needed",
        "applied": false
      },
      {
        "layer": "short_message_resolver",
        "override_reason": "Affirmative 'yes' in stage 'job-ready' → 'job.request'",
        "applied": true
      }
    ],
    "confidence": 0.9
  }
}
```

**Key Points:**
- Raw intent is `general.chat` (OpenAI misclassified "yes")
- Layer 4 (short_message_resolver) detects affirmative word
- Stage-specific override applies: `affirmative_override: "job.request"`
- Final intent is `job.request`

### Scenario 2: Explicit Job Request

**Input:**
```json
{
  "message": "Approve this job and create the work order",
  "context": {
    "flow_state": {
      "stage": "job-ready",
      "question_index": 4
    },
    "active_incident_id": "INC-123",
    "persona": "tenant"
  }
}
```

**Output:**
```json
{
  "intent": "job.request",
  "summary": "Work order requested",
  "reply": "Perfect. I'll move ahead with creating a work order.",
  "entities": {},
  "actions": ["create_job"],
  "persona": "tenant",
  "reasoning": {
    "raw_intent": "job.request",
    "final_intent": "job.request",
    "stage": "job-ready",
    "layers_applied": [
      {
        "layer": "flow_state_override",
        "override_reason": "No override needed",
        "applied": false
      },
      {
        "layer": "safety_guard",
        "override_reason": "No safety override needed",
        "applied": false
      },
      {
        "layer": "short_message_resolver",
        "override_reason": "Not a short message",
        "applied": false
      }
    ],
    "confidence": 0.95
  }
}
```

---

## Approval Pending Stage

### Scenario 1: Approval ("yes")

**Input:**
```json
{
  "message": "yes, approve",
  "context": {
    "flow_state": {
      "stage": "approval_pending",
      "last_ai_prompt": "Would you like to approve this work order?"
    },
    "active_job_id": "JOB-456",
    "persona": "landlord"
  }
}
```

**Output:**
```json
{
  "intent": "approval.decision",
  "summary": "Approval decision made",
  "reply": "Great! I've recorded your approval and will proceed with the work order.",
  "entities": {},
  "actions": ["process_approval"],
  "persona": "landlord",
  "reasoning": {
    "raw_intent": "general.chat",
    "final_intent": "approval.decision",
    "stage": "approval_pending",
    "layers_applied": [
      {
        "layer": "flow_state_override",
        "override_reason": "No override needed",
        "applied": false
      },
      {
        "layer": "safety_guard",
        "override_reason": "No safety override needed",
        "applied": false
      },
      {
        "layer": "short_message_resolver",
        "override_reason": "Affirmative 'yes' in stage 'approval_pending' → 'approval.decision'",
        "applied": true
      }
    ],
    "confidence": 0.95
  }
}
```

### Scenario 2: Rejection ("no")

**Input:**
```json
{
  "message": "no, reject this",
  "context": {
    "flow_state": {
      "stage": "approval_pending"
    },
    "active_job_id": "JOB-456",
    "persona": "landlord"
  }
}
```

**Output:**
```json
{
  "intent": "approval.decision",
  "summary": "Approval decision made",
  "reply": "I've recorded your decision. The work order will not proceed.",
  "entities": {},
  "actions": ["process_rejection"],
  "persona": "landlord",
  "reasoning": {
    "raw_intent": "general.chat",
    "final_intent": "approval.decision",
    "stage": "approval_pending",
    "layers_applied": [
      {
        "layer": "flow_state_override",
        "override_reason": "No override needed",
        "applied": false
      },
      {
        "layer": "safety_guard",
        "override_reason": "No safety override needed",
        "applied": false
      },
      {
        "layer": "short_message_resolver",
        "override_reason": "Negative 'no' in stage 'approval_pending' → 'approval.decision' (rejected)",
        "applied": true,
        "decision": "rejected"
      }
    ],
    "confidence": 0.95
  }
}
```

### Scenario 3: Blocked Intent During Approval

**Input:**
```json
{
  "message": "I have a new incident to report",
  "context": {
    "flow_state": {
      "stage": "approval_pending"
    },
    "active_job_id": "JOB-456",
    "persona": "landlord"
  }
}
```

**Output:**
```json
{
  "intent": "approval.decision",
  "summary": "Approval decision made",
  "reply": "I'm waiting for your approval decision. Would you like to approve or reject this work order?",
  "entities": {},
  "actions": ["await_approval"],
  "persona": "landlord",
  "reasoning": {
    "raw_intent": "incident.report",
    "final_intent": "approval.decision",
    "stage": "approval_pending",
    "layers_applied": [
      {
        "layer": "flow_state_override",
        "override_reason": "Intent 'incident.report' blocked in stage 'approval_pending', using default 'approval.decision'",
        "applied": true
      },
      {
        "layer": "safety_guard",
        "override_reason": "No safety override needed",
        "applied": false
      },
      {
        "layer": "short_message_resolver",
        "override_reason": "Not a short message",
        "applied": false
      }
    ],
    "confidence": 0.7
  }
}
```

**Key Points:**
- All intents except `approval.decision` are blocked during approval
- Layer 2 forces override to `approval.decision`
- Response prompts user to make approval decision

---

## Job Stage

### Scenario 1: Job Status Inquiry

**Input:**
```json
{
  "message": "What's the status of my job?",
  "context": {
    "flow_state": {
      "stage": "job"
    },
    "active_job_id": "JOB-456",
    "persona": "tenant"
  }
}
```

**Output:**
```json
{
  "intent": "job.status",
  "summary": "What's the status of my job?",
  "reply": "Your work order is currently in progress. Let me know if you need an update.",
  "entities": {},
  "actions": ["check_job_status"],
  "persona": "tenant",
  "reasoning": {
    "raw_intent": "job.status",
    "final_intent": "job.status",
    "stage": "job",
    "layers_applied": [
      {
        "layer": "flow_state_override",
        "override_reason": "No override needed",
        "applied": false
      },
      {
        "layer": "safety_guard",
        "override_reason": "No safety override needed",
        "applied": false
      },
      {
        "layer": "short_message_resolver",
        "override_reason": "Not a short message",
        "applied": false
      }
    ],
    "confidence": 0.9
  }
}
```

---

## Error Scenarios

### Scenario 1: Attempt to Create New Incident During Active Incident

**Input:**
```json
{
  "message": "Emergency! Fire in the kitchen!",
  "context": {
    "flow_state": {
      "stage": "discovery",
      "question_index": 2
    },
    "active_incident_id": "INC-123",
    "persona": "tenant"
  }
}
```

**Output:**
```json
{
  "intent": "incident.followup",
  "summary": "Discovery question answered",
  "reply": "Thanks for that information. I'm recording your response.",
  "entities": {
    "severity": "emergency",
    "category": "general"
  },
  "actions": ["continue_discovery"],
  "persona": "tenant",
  "reasoning": {
    "raw_intent": "incident.report",
    "final_intent": "incident.followup",
    "stage": "discovery",
    "layers_applied": [
      {
        "layer": "flow_state_override",
        "override_reason": "Intent 'incident.report' blocked in stage 'discovery', using default 'discovery.response'",
        "applied": true
      },
      {
        "layer": "safety_guard",
        "override_reason": "Cannot create new incident - active incident INC-123 exists",
        "applied": true
      },
      {
        "layer": "short_message_resolver",
        "override_reason": "Not a short message",
        "applied": false
      }
    ],
    "confidence": 0.9
  }
}
```

**Key Points:**
- Layer 2 blocks `incident.report` (not allowed in discovery)
- Layer 3 prevents new incident creation (safety guard)
- System treats as `incident.followup` instead

### Scenario 2: Attempt to Create New Job During Active Job

**Input:**
```json
{
  "message": "Create a new job for the bathroom leak",
  "context": {
    "flow_state": {
      "stage": "job"
    },
    "active_job_id": "JOB-456",
    "persona": "tenant"
  }
}
```

**Output:**
```json
{
  "intent": "job.inquiry",
  "summary": "What's the status of my job?",
  "reply": "Your work order is currently in progress. Let me know if you need an update.",
  "entities": {},
  "actions": ["check_job_status"],
  "persona": "tenant",
  "reasoning": {
    "raw_intent": "job.request",
    "final_intent": "job.inquiry",
    "stage": "job",
    "layers_applied": [
      {
        "layer": "flow_state_override",
        "override_reason": "No override needed",
        "applied": false
      },
      {
        "layer": "safety_guard",
        "override_reason": "Cannot create new job - active job JOB-456 exists",
        "applied": true
      },
      {
        "layer": "short_message_resolver",
        "override_reason": "Not a short message",
        "applied": false
      }
    ],
    "confidence": 0.8
  }
}
```

**Key Points:**
- Layer 3 (safety guard) prevents new job creation
- Intent converted from `job.request` to `job.inquiry`
- Response redirects to current job status

---

## Summary

### Intent Override Hierarchy

1. **Layer 2 (Flow State Override)**: Highest priority - enforces stage rules
2. **Layer 3 (Safety Guard)**: Prevents invalid state transitions
3. **Layer 4 (Short Message Resolver)**: Disambiguates affirmative/negative words
4. **Original Intent**: Used if no overrides apply

### Common Patterns

| User Message | Stage | Raw Intent | Final Intent | Override Layer |
|--------------|-------|------------|--------------|----------------|
| "yes" | discovery | general.chat | discovery.response | Layer 2 |
| "yes" | job-ready | general.chat | job.request | Layer 4 |
| "yes" | approval_pending | general.chat | approval.decision | Layer 4 |
| "Approve this job" | job-ready | general.chat | job.request | Layer 4 |
| "Emergency leak!" | discovery | incident.report | incident.followup | Layer 2 + 3 |
| "Create a job" | job (active) | job.request | job.inquiry | Layer 3 |

### Testing Checklist

Use these scenarios to validate the system:

- ✅ "yes" during discovery → discovery.response
- ✅ "yes" during job-ready → job.request
- ✅ "yes" during approval → approval.decision
- ✅ "no" during approval → approval.decision (rejected)
- ✅ New incident during discovery → blocked (incident.followup)
- ✅ New job during active job → blocked (job.inquiry)
- ✅ Greeting during idle → greeting
- ✅ Long descriptive answer → keeps original intent

---

**End of Example JSON Responses**
