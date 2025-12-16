/**
 * Parse diagnostic data from AI message text
 */

export interface ParsedDiagnosticData {
  hasDiagnostic: boolean;
  diagnosticResult?: {
    diagnosis?: string;
    severity?: string;
    urgency?: string;
    estimatedCost?: string;
    recommendations?: string[];
    description?: string;
  };
  photoAnalysis?: {
    findings?: string[];
    concerns?: string[];
    caution?: string[];
  };
  nextSteps?: string[];
  safetyConsiderations?: string[];
  questions?: string[];
  choices?: string[]; // NEW: Parse "Would you like me to" choices
}

export function parseDiagnosticData(text: string): ParsedDiagnosticData {
  if (!text) {
    return { hasDiagnostic: false };
  }

  const result: ParsedDiagnosticData = {
    hasDiagnostic: false,
  };

  // Check if this looks like a diagnostic message
  const diagnosticKeywords = [
    'diagnostic results',
    'diagnosis:',
    'photo analysis',
    'severity:',
    'urgency:',
    'estimated cost:',
    'recommendations:',
    'next steps',
    'safety considerations',
    'would you like me to',
    'a couple quick questions',
  ];

  const lowerText = text.toLowerCase();
  const hasDiagnosticContent = diagnosticKeywords.some((keyword) =>
    lowerText.includes(keyword)
  );

  if (!hasDiagnosticContent) {
    return result;
  }

  result.hasDiagnostic = true;

  // Parse Diagnostic Results section
  const diagnosticMatch = text.match(
    /(?:Diagnostic results|🔧 Diagnostic results|🔎 Diagnostic results)[:\s]*\(from diagnostic tool\)?\s*([\s\S]*?)(?=\n\n|Photo analysis|Next steps|What this means|$)/i
  );

  if (diagnosticMatch) {
    const diagnosticText = diagnosticMatch[1];

    // Extract diagnosis
    const diagnosisMatch = diagnosticText.match(/(?:^|\n)\s*-?\s*Diagnosis:\s*(.+?)(?:\n|$)/i);
    const diagnosis = diagnosisMatch ? diagnosisMatch[1].trim() : undefined;

    // Extract severity
    const severityMatch = diagnosticText.match(/(?:^|\n)\s*-?\s*Severity:\s*(.+?)(?:\n|$)/i);
    const severity = severityMatch ? severityMatch[1].trim() : undefined;

    // Extract urgency
    const urgencyMatch = diagnosticText.match(/(?:^|\n)\s*-?\s*Urgency:\s*(.+?)(?:\n|$)/i);
    const urgency = urgencyMatch ? urgencyMatch[1].trim() : undefined;

    // Extract estimated cost
    const costMatch = diagnosticText.match(/(?:^|\n)\s*-?\s*Estimated cost:\s*(.+?)(?:\n|$)/i);
    const estimatedCost = costMatch ? costMatch[1].trim() : undefined;

    // Extract recommendations
    const recsMatch = diagnosticText.match(/(?:^|\n)\s*-?\s*Recommendations?:\s*(.+?)(?:\n|$)/i);
    const recommendations = recsMatch ? [recsMatch[1].trim()] : undefined;

    result.diagnosticResult = {
      diagnosis,
      severity,
      urgency,
      estimatedCost,
      recommendations,
    };
  }

  // Parse Photo Analysis section
  const photoAnalysisMatch = text.match(
    /Photo analysis[:\s]*\(based on your image\)?\s*([\s\S]*?)(?=\n\n|Next steps|Safety|$)/i
  );

  if (photoAnalysisMatch) {
    const photoText = photoAnalysisMatch[1];
    result.photoAnalysis = {
      findings: extractLines(photoText, ['Visible', 'Indicates']),
      concerns: extractLines(photoText, ['Indicates potential', 'leak']),
      caution: extractLines(photoText, ['Caution', 'hazardous', 'avoid']),
    };
  }

  // Parse Next Steps
  const nextStepsMatch = text.match(
    /Next steps I can take for you[:\s]*([\s\S]*?)(?=\n\n|A couple quick questions|Would you like|$)/i
  );

  if (nextStepsMatch) {
    const stepsText = nextStepsMatch[1];
    result.nextSteps = extractBulletPoints(stepsText);
  }

  // Parse Questions - numbered or bulleted
  const questionsMatch = text.match(
    /(?:A couple quick questions|questions to tailor the plan)[:\s]*([\s\S]*?)(?=\n\nWould you like|$)/i
  );

  if (questionsMatch) {
    const questionsText = questionsMatch[1];
    result.questions = extractBulletPoints(questionsText);
  }

  // Parse Choices - "Would you like me to" options
  const choicesMatch = text.match(
    /Would you like me to[:\s]*([\s\S]*?)$/i
  );

  if (choicesMatch) {
    const choicesText = choicesMatch[1];
    // Split by "or" to get multiple options
    const options = choicesText.split(/,\s*or\s+|\s+or\s+/);
    result.choices = options.map(opt => opt.trim()).filter(opt => opt.length > 0);
  }

  // Parse Safety Considerations
  const safetyMatch = text.match(
    /Safety considerations?[:\s]*([\s\S]*?)(?=\n\n|Next steps|$)/i
  );

  if (safetyMatch) {
    const safetyText = safetyMatch[1];
    result.safetyConsiderations = extractBulletPoints(safetyText);
  }

  return result;
}

// Helper: Extract a single field value
function extractField(text: string, fieldName: string): string | undefined {
  const regex = new RegExp(`${fieldName}[:\\s]+([^\\n]+)`, 'i');
  const match = text.match(regex);
  return match ? match[1].trim() : undefined;
}

// Helper: Extract bullet points or numbered lists
function extractBulletPoints(text: string, section?: string): string[] {
  let searchText = text;

  // If section specified, find that section first
  if (section) {
    const sectionRegex = new RegExp(`${section}[:\\s]*([\s\S]*)`, 'i');
    const sectionMatch = text.match(sectionRegex);
    if (sectionMatch) {
      searchText = sectionMatch[1];
    } else {
      return [];
    }
  }

  const lines = searchText.split('\n');
  const items: string[] = [];

  for (const line of lines) {
    const trimmed = line.trim();
    // Match bullet points (•, -, *) or numbered lists
    const bulletMatch = trimmed.match(/^[•\-*]\s+(.+)$/);
    const numberMatch = trimmed.match(/^\d+[\.)]\s+(.+)$/);

    if (bulletMatch) {
      items.push(bulletMatch[1].trim());
    } else if (numberMatch) {
      items.push(numberMatch[1].trim());
    }
  }

  return items;
}

// Helper: Extract lines containing specific keywords
function extractLines(text: string, keywords: string[]): string[] {
  const lines = text.split('\n');
  const results: string[] = [];

  for (const line of lines) {
    const trimmed = line.trim();
    if (keywords.some((keyword) => trimmed.toLowerCase().includes(keyword.toLowerCase()))) {
      // Remove bullet points if present
      const cleaned = trimmed.replace(/^[•\-*]\s+/, '').trim();
      if (cleaned) {
        results.push(cleaned);
      }
    }
  }

  return results;
}

/**
 * Determine severity level from diagnostic data
 */
export function determineSeverity(
  diagnosticData: ParsedDiagnosticData,
  metadata?: { severity?: string; urgency?: string }
): 'low' | 'medium' | 'high' | 'urgent' {
  // Check metadata first
  const metaSeverity = metadata?.severity?.toLowerCase();
  const metaUrgency = metadata?.urgency?.toLowerCase();

  if (metaSeverity === 'emergency' || metaUrgency === 'immediate') return 'urgent';
  if (metaSeverity === 'high' || metaUrgency === 'urgent') return 'high';
  if (metaSeverity === 'low' || metaUrgency === 'routine') return 'low';

  // Check diagnostic result
  const diagSeverity = diagnosticData.diagnosticResult?.severity?.toLowerCase();
  const diagUrgency = diagnosticData.diagnosticResult?.urgency?.toLowerCase();

  if (diagSeverity === 'emergency' || diagUrgency === 'immediate') return 'urgent';
  if (diagSeverity === 'high' || diagUrgency === 'urgent') return 'high';
  if (diagSeverity === 'low' || diagUrgency === 'routine') return 'low';

  // Check for safety considerations
  if (
    diagnosticData.safetyConsiderations &&
    diagnosticData.safetyConsiderations.length > 0
  ) {
    return 'high';
  }

  return 'medium';
}
