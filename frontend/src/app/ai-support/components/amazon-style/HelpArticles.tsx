/**
 * HelpArticles - Amazon-style help articles section
 *
 * Shows recommended help articles
 */

"use client";

import { motion } from "framer-motion";
import { FileText, ChevronRight } from "lucide-react";

interface HelpArticle {
  id: string;
  title: string;
  category: string;
  helpful: number;
}

interface HelpArticlesProps {
  persona: string;
  onArticleClick?: (articleId: string, articleTitle: string) => void;
}

export default function HelpArticles({ persona, onArticleClick }: HelpArticlesProps) {
  const getArticles = (): HelpArticle[] => {
    if (persona === "tenant") {
      return [
        {
          id: "1",
          title: "How to report a maintenance issue",
          category: "Maintenance",
          helpful: 234,
        },
        {
          id: "2",
          title: "Understanding your rent payment options",
          category: "Billing",
          helpful: 189,
        },
        {
          id: "3",
          title: "What to do in case of emergency",
          category: "Safety",
          helpful: 156,
        },
        {
          id: "4",
          title: "Lease renewal process explained",
          category: "Lease",
          helpful: 142,
        },
        {
          id: "5",
          title: "Tenant rights and responsibilities",
          category: "Legal",
          helpful: 128,
        },
      ];
    } else if (persona === "landlord") {
      return [
        {
          id: "1",
          title: "How to triage and prioritize maintenance requests",
          category: "Operations",
          helpful: 201,
        },
        {
          id: "2",
          title: "Managing contractor bids effectively",
          category: "Contractors",
          helpful: 178,
        },
        {
          id: "3",
          title: "Best practices for tenant communication",
          category: "Communication",
          helpful: 165,
        },
        {
          id: "4",
          title: "Understanding property maintenance schedules",
          category: "Maintenance",
          helpful: 143,
        },
      ];
    } else if (persona === "contractor") {
      return [
        {
          id: "1",
          title: "How to submit a competitive bid",
          category: "Bidding",
          helpful: 187,
        },
        {
          id: "2",
          title: "Documenting work completion properly",
          category: "Documentation",
          helpful: 164,
        },
        {
          id: "3",
          title: "Managing multiple job assignments",
          category: "Workflow",
          helpful: 152,
        },
        {
          id: "4",
          title: "Payment and invoicing guidelines",
          category: "Billing",
          helpful: 139,
        },
      ];
    }

    return [];
  };

  const articles = getArticles();

  return (
    <div className="p-6 bg-slate-800/40 border border-slate-700/60 rounded-xl">
      <div className="flex items-center gap-2 mb-4">
        <FileText className="w-5 h-5 text-emerald-400" />
        <h3 className="text-lg font-semibold text-slate-100">
          Find answers in help articles
        </h3>
      </div>

      <div className="space-y-2">
        {articles.map((article, index) => (
          <motion.button
            key={article.id}
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: index * 0.05 }}
            onClick={() => onArticleClick?.(article.id, article.title)}
            className="w-full p-3 bg-slate-800/60 border border-slate-700/60 hover:border-emerald-500/50 rounded-lg transition-all duration-200 flex items-center justify-between group text-left"
          >
            <div className="flex-1 min-w-0">
              <h4 className="font-medium text-slate-100 mb-1 text-sm">
                {article.title}
              </h4>
              <div className="flex items-center gap-3 text-xs text-slate-400">
                <span>{article.category}</span>
                <span>•</span>
                <span>{article.helpful} found this helpful</span>
              </div>
            </div>
            <ChevronRight className="w-4 h-4 text-slate-500 group-hover:text-emerald-400 transition-colors flex-shrink-0 ml-2" />
          </motion.button>
        ))}
      </div>

      <button className="w-full mt-4 py-2 text-sm text-emerald-400 hover:text-emerald-300 transition-colors">
        View all articles →
      </button>
    </div>
  );
}
