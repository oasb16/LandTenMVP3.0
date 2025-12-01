/**
 * HelpHub - Amazon-style Help Center Landing
 *
 * Shows personalized greeting, search, categories, and items grid
 */

"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { Search, ChevronRight, Package, Home, Wrench, FileText, AlertCircle } from "lucide-react";
import type { Persona } from "@/types/ai-support";

interface HelpHubProps {
  userName: string;
  persona: Persona;
  onSelectItem: (itemId: string, itemType: string, itemTitle: string) => void;
  onLaunchChat: () => void;
}

interface HelpItem {
  id: string;
  type: string;
  title: string;
  subtitle: string;
  status?: string;
  icon: any;
  imageUrl?: string;
}

export default function HelpHub({
  userName,
  persona,
  onSelectItem,
  onLaunchChat,
}: HelpHubProps) {
  const [selectedTab, setSelectedTab] = useState("all");
  const [searchQuery, setSearchQuery] = useState("");

  // Generate persona-specific items
  const getItems = (): HelpItem[] => {
    if (persona === "tenant") {
      return [
        {
          id: "prop-1",
          type: "property",
          title: "Sunset Apartments - Unit 204",
          subtitle: "Active lease",
          status: "Current",
          icon: Home,
        },
        {
          id: "inc-1",
          type: "incident",
          title: "Kitchen Sink Leaking",
          subtitle: "Reported 2 days ago",
          status: "In Progress",
          icon: AlertCircle,
        },
        {
          id: "inc-2",
          type: "incident",
          title: "Broken HVAC",
          subtitle: "Reported 5 days ago",
          status: "Pending",
          icon: AlertCircle,
        },
        {
          id: "bill-1",
          type: "billing",
          title: "November Rent Payment",
          subtitle: "Due in 5 days",
          status: "Pending",
          icon: FileText,
        },
      ];
    } else if (persona === "landlord") {
      return [
        {
          id: "prop-1",
          type: "property",
          title: "Sunset Apartments",
          subtitle: "12 units",
          status: "Active",
          icon: Home,
        },
        {
          id: "inc-1",
          type: "incident",
          title: "Unit 204 - Kitchen Sink",
          subtitle: "Needs triage",
          status: "New",
          icon: AlertCircle,
        },
        {
          id: "job-1",
          type: "job",
          title: "HVAC Repair - Unit 305",
          subtitle: "3 bids received",
          status: "Pending",
          icon: Wrench,
        },
        {
          id: "job-2",
          type: "job",
          title: "Plumbing Fix - Unit 204",
          subtitle: "In progress",
          status: "Active",
          icon: Wrench,
        },
      ];
    } else if (persona === "contractor") {
      return [
        {
          id: "job-1",
          type: "available_job",
          title: "HVAC Repair - Sunset Apts",
          subtitle: "Budget: $500-2000",
          status: "Open",
          icon: Package,
        },
        {
          id: "job-2",
          type: "assigned_job",
          title: "Plumbing Fix - Oak Street",
          subtitle: "Accepted, not started",
          status: "Assigned",
          icon: Wrench,
        },
        {
          id: "job-3",
          type: "assigned_job",
          title: "Electrical Repair - Main St",
          subtitle: "In progress",
          status: "Active",
          icon: Wrench,
        },
      ];
    }
    return [];
  };

  const items = getItems();

  const getGreeting = () => {
    if (persona === "tenant") {
      return `Hi, ${userName}. Thanks for being a valued tenant.`;
    } else if (persona === "landlord") {
      return `Hi, ${userName}. Welcome to your property management hub.`;
    } else if (persona === "contractor") {
      return `Hi, ${userName}. Here are your jobs and opportunities.`;
    }
    return `Hi, ${userName}`;
  };

  const getTabs = () => {
    if (persona === "tenant") {
      return [
        { id: "all", label: "All" },
        { id: "properties", label: "Properties" },
        { id: "incidents", label: "Maintenance" },
        { id: "billing", label: "Billing" },
      ];
    } else if (persona === "landlord") {
      return [
        { id: "all", label: "All" },
        { id: "properties", label: "Properties" },
        { id: "incidents", label: "Incidents" },
        { id: "jobs", label: "Jobs" },
      ];
    } else if (persona === "contractor") {
      return [
        { id: "all", label: "All" },
        { id: "available", label: "Available Jobs" },
        { id: "assigned", label: "My Jobs" },
        { id: "completed", label: "Completed" },
      ];
    }
    return [{ id: "all", label: "All" }];
  };

  const tabs = getTabs();

  return (
    <div className="h-full flex flex-col bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      {/* Header */}
      <div className="border-b border-slate-700/60 bg-slate-800/40 backdrop-blur-sm">
        <div className="max-w-6xl mx-auto px-6 py-4">
          {/* Greeting */}
          <h1 className="text-xl font-semibold text-slate-100 mb-4">
            {getGreeting()}
          </h1>

          {/* Search Bar */}
          <div className="relative mb-4">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search help topics..."
              className="w-full pl-12 pr-4 py-3 bg-slate-800/60 border border-slate-700/60 rounded-xl text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500/50"
            />
          </div>

          {/* Category Tabs */}
          <div className="flex gap-2 overflow-x-auto pb-1">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setSelectedTab(tab.id)}
                className={`
                  px-4 py-2 rounded-lg font-medium whitespace-nowrap transition-all
                  ${selectedTab === tab.id
                    ? "bg-emerald-500 text-emerald-950"
                    : "bg-slate-700/40 text-slate-300 hover:bg-slate-700/60"
                  }
                `}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Items Grid */}
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-6xl mx-auto px-6 py-6">
          <h2 className="text-lg font-semibold text-slate-100 mb-4">
            Your Items
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
            {items.map((item, index) => {
              const Icon = item.icon;
              return (
                <motion.button
                  key={item.id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.05 }}
                  onClick={() => onSelectItem(item.id, item.type, item.title)}
                  className="flex items-start gap-4 p-4 bg-slate-800/60 border border-slate-700/60 hover:border-emerald-500/50 rounded-xl transition-all duration-200 text-left group"
                >
                  {/* Icon */}
                  <div className="flex-shrink-0 w-12 h-12 rounded-lg bg-slate-700/60 flex items-center justify-center">
                    <Icon className="w-6 h-6 text-emerald-400" />
                  </div>

                  {/* Content */}
                  <div className="flex-1 min-w-0">
                    <h3 className="font-semibold text-slate-100 mb-1 truncate">
                      {item.title}
                    </h3>
                    <p className="text-sm text-slate-400 truncate">
                      {item.subtitle}
                    </p>
                    {item.status && (
                      <span className="inline-block mt-2 px-2 py-0.5 text-xs font-medium rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                        {item.status}
                      </span>
                    )}
                  </div>

                  {/* Arrow */}
                  <ChevronRight className="w-5 h-5 text-slate-500 group-hover:text-emerald-400 transition-colors flex-shrink-0" />
                </motion.button>
              );
            })}
          </div>

          {/* Load More */}
          <button className="w-full py-3 border border-slate-700/60 rounded-xl text-slate-300 hover:bg-slate-800/40 transition-colors">
            Load more
          </button>
        </div>

        {/* Quick Chat Option */}
        <div className="max-w-6xl mx-auto px-6 pb-6">
          <div className="p-4 bg-blue-500/10 border border-blue-500/30 rounded-xl">
            <h3 className="font-semibold text-blue-400 mb-2">
              Can't find what you're looking for?
            </h3>
            <p className="text-sm text-slate-300 mb-3">
              Start a conversation with our AI assistant for personalized help.
            </p>
            <button
              onClick={onLaunchChat}
              className="px-4 py-2 bg-emerald-500 hover:bg-emerald-400 text-emerald-950 rounded-lg font-semibold transition-colors"
            >
              Chat with Assistant
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
