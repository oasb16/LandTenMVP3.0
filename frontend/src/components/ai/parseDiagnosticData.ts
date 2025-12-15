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
  };
  photoAnalysis?: {
    findings?: string[];
    concerns?: string[];
    caution?: string[];
  };
  nextSteps?: string[];
  safetyConsiderations?: string[];
  questions?: string[];
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
    /(?:Diagnostic results|🔧 Diagnostic results)[:\s]*\(from diagnostic tool\)?\s*([\s\S]*?)(?=\n\n|Photo analysis|Next steps|$)/i
  );

  if (diagnosticMatch) {
    const diagnosticText = diagnosticMatch[1];
    result.diagnosticResult = {
      diagnosis: extractField(diagnosticText, 'Diagnosis'),
      severity: extractField(diagnosticText, 'Severity'),
      urgency: extractField(diagnosticText, 'Urgency'),
      estimatedCost: extractField(diagnosticText, 'Estimated cost'),
      recommendations: extractBulletPoints(diagnosticText, 'Recommendations'),
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
    /Next steps[:\s]*(?:I can take for you|we can take)?[:\s]*([\s\S]*?)(?=\n\n|A few quick questions|Would you like|$)/i
  );

  if (nextStepsMatch) {
    const stepsText = nextStepsMatch[1];
    result.nextSteps = extractBulletPoints(stepsText);
  }

  // Parse Safety Considerations
  const safetyMatch = text.match(
    /Safety considerations?[:\s]*([\s\S]*?)(?=\n\n|Next steps|$)/i
  );

  if (safetyMatch) {
    const safetyText = safetyMatch[1];
    result.safetyConsiderations = extractBulletPoints(safetyText);
  }

  // Parse Questions
  const questionsMatch = text.match(
    /(?:A few quick questions|questions to refine)[:\s]*([\s\S]*?)(?=\n\nWould you like|$)/i
  );

  if (questionsMatch) {
    const questionsText = questionsMatch[1];
    result.questions = extractBulletPoints(questionsText);
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
