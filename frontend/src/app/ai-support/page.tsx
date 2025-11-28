/**
 * AI Support Experience Page
 *
 * Amazon-style guided support flow powered by Stream Chat and LLM orchestration
 */

import AIChatContainer from "./components/AIChatContainer";
import "./ai-support.css";

export const metadata = {
  title: "AI Support Assistant | LandTen",
  description: "Get instant help with our AI-powered support assistant",
};

export default function AISupportPage() {
  return <AIChatContainer mode="guided" />;
}
