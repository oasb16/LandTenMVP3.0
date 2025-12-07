"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useSession } from "next-auth/react";
import { Upload, Camera, CheckCircle, AlertCircle, X } from "lucide-react";

type Category = "plumbing" | "electrical" | "hvac" | "appliance" | "structural" | "pest" | "other";
type Urgency = "low" | "medium" | "high" | "emergency";

const categories: { value: Category; label: string }[] = [
  { value: "plumbing", label: "Plumbing" },
  { value: "electrical", label: "Electrical" },
  { value: "hvac", label: "HVAC" },
  { value: "appliance", label: "Appliance" },
  { value: "structural", label: "Structural" },
  { value: "pest", label: "Pest Control" },
  { value: "other", label: "Other" },
];

const urgencyLevels: { value: Urgency; label: string; color: string }[] = [
  { value: "low", label: "Low", color: "bg-green-600 hover:bg-green-500" },
  { value: "medium", label: "Medium", color: "bg-yellow-600 hover:bg-yellow-500" },
  { value: "high", label: "High", color: "bg-orange-600 hover:bg-orange-500" },
  { value: "emergency", label: "Emergency", color: "bg-red-600 hover:bg-red-500" },
];

const discoveryQuestions: Record<Category, string[]> = {
  plumbing: [
    "When did you first notice this issue?",
    "Is there active water leaking?",
    "Have you tried any temporary fixes?",
    "Additional details?",
  ],
  electrical: [
    "When did this start?",
    "Are any outlets or switches affected?",
    "Have you checked the circuit breaker?",
    "Additional details?",
  ],
  hvac: [
    "When did you first notice the problem?",
    "Is the system making unusual noises?",
    "What is the current temperature?",
    "Additional details?",
  ],
  appliance: [
    "Which appliance is affected?",
    "When did it stop working?",
    "What error messages do you see?",
    "Additional details?",
  ],
  structural: [
    "When did you notice this issue?",
    "Is the problem getting worse?",
    "Have you noticed any safety concerns?",
    "Additional details?",
  ],
  pest: [
    "What type of pest have you seen?",
    "When did you first notice them?",
    "How frequently do you see them?",
    "Additional details?",
  ],
  other: [
    "When did this start?",
    "How often does this occur?",
    "Have you attempted any fixes?",
    "Additional details?",
  ],
};

export default function NewIncidentPage() {
  const router = useRouter();
  const { data: session } = useSession();

  // Form state
  const [step, setStep] = useState(1);
  const [incidentId, setIncidentId] = useState<string | null>(null);

  // Step 1: Basic Info
  const [title, setTitle] = useState("");
  const [category, setCategory] = useState<Category>("plumbing");
  const [urgency, setUrgency] = useState<Urgency>("medium");
  const [description, setDescription] = useState("");

  // Step 2: Photos
  const [photos, setPhotos] = useState<File[]>([]);
  const [photoPreviews, setPhotoPreviews] = useState<string[]>([]);
  const [uploadProgress, setUploadProgress] = useState(0);

  // Step 3: Discovery Questions
  const [answers, setAnswers] = useState<Record<string, string>>({});

  // UI state
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const getToken = () => {
    // Get token from session or localStorage
    return session?.user?.accessToken || localStorage.getItem("token") || "";
  };

  // Step 1: Submit basic info
  const handleBasicInfoSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const res = await fetch("/api/v1/incidents/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${getToken()}`,
        },
        body: JSON.stringify({
          title,
          category,
          urgency,
          description,
        }),
      });

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || "Failed to create incident");
      }

      const data = await res.json();
      setIncidentId(data.incident_id);
      setStep(2);
    } catch (err: any) {
      console.error("Error creating incident:", err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // Step 2: Handle photo selection
  const handlePhotoChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    setPhotos((prev) => [...prev, ...files]);

    // Create previews
    files.forEach((file) => {
      const reader = new FileReader();
      reader.onloadend = () => {
        setPhotoPreviews((prev) => [...prev, reader.result as string]);
      };
      reader.readAsDataURL(file);
    });
  };

  // Remove photo
  const removePhoto = (index: number) => {
    setPhotos((prev) => prev.filter((_, i) => i !== index));
    setPhotoPreviews((prev) => prev.filter((_, i) => i !== index));
  };

  // Step 2: Upload photos
  const handlePhotoSubmit = async () => {
    if (!incidentId) return;

    setLoading(true);
    setError(null);

    try {
      // Upload each photo
      for (let i = 0; i < photos.length; i++) {
        const formData = new FormData();
        formData.append("file", photos[i]);

        const res = await fetch(`/api/v1/incidents/${incidentId}/photos`, {
          method: "POST",
          headers: {
            Authorization: `Bearer ${getToken()}`,
          },
          body: formData,
        });

        if (!res.ok) {
          throw new Error(`Failed to upload photo ${i + 1}`);
        }

        setUploadProgress(((i + 1) / photos.length) * 100);
      }

      setStep(3);
    } catch (err: any) {
      console.error("Error uploading photos:", err);
      setError(err.message);
    } finally {
      setLoading(false);
      setUploadProgress(0);
    }
  };

  // Skip photos
  const handleSkipPhotos = () => {
    setStep(3);
  };

  // Step 3: Submit discovery answers
  const handleDiscoverySubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!incidentId) return;

    setLoading(true);
    setError(null);

    try {
      const res = await fetch(`/api/v1/incidents/${incidentId}/discovery`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${getToken()}`,
        },
        body: JSON.stringify({ answers }),
      });

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || "Failed to submit discovery answers");
      }

      // Success! Redirect to incidents list
      router.push("/tenant/incidents");
    } catch (err: any) {
      console.error("Error submitting discovery:", err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 py-8 px-4">
      <div className="max-w-3xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold mb-2">Report an Incident</h1>
          <div className="flex items-center gap-2">
            <div className={`w-8 h-8 rounded-full flex items-center justify-center ${step >= 1 ? "bg-blue-600" : "bg-slate-700"}`}>
              {step > 1 ? <CheckCircle className="w-5 h-5" /> : "1"}
            </div>
            <div className={`flex-1 h-1 ${step >= 2 ? "bg-blue-600" : "bg-slate-700"}`} />
            <div className={`w-8 h-8 rounded-full flex items-center justify-center ${step >= 2 ? "bg-blue-600" : "bg-slate-700"}`}>
              {step > 2 ? <CheckCircle className="w-5 h-5" /> : "2"}
            </div>
            <div className={`flex-1 h-1 ${step >= 3 ? "bg-blue-600" : "bg-slate-700"}`} />
            <div className={`w-8 h-8 rounded-full flex items-center justify-center ${step >= 3 ? "bg-blue-600" : "bg-slate-700"}`}>
              3
            </div>
          </div>
          <div className="flex justify-between text-sm text-slate-400 mt-2">
            <span>Basic Info</span>
            <span>Photos</span>
            <span>Details</span>
          </div>
        </div>

        {/* Error Display */}
        {error && (
          <div className="mb-6 p-4 bg-red-900/50 border border-red-500 rounded-lg flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
            <div>
              <h3 className="font-semibold text-red-200">Error</h3>
              <p className="text-red-300 text-sm">{error}</p>
            </div>
          </div>
        )}

        {/* Step 1: Basic Info */}
        {step === 1 && (
          <form onSubmit={handleBasicInfoSubmit} className="space-y-6">
            <div className="bg-slate-900 rounded-lg p-6 border border-slate-800">
              <h2 className="text-xl font-semibold mb-4">Basic Information</h2>

              {/* Title */}
              <div className="mb-4">
                <label className="block text-sm font-medium mb-2">
                  Title <span className="text-red-400">*</span>
                </label>
                <input
                  type="text"
                  required
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  className="w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="Brief description of the issue"
                />
              </div>

              {/* Category */}
              <div className="mb-4">
                <label className="block text-sm font-medium mb-2">
                  Category <span className="text-red-400">*</span>
                </label>
                <select
                  required
                  value={category}
                  onChange={(e) => setCategory(e.target.value as Category)}
                  className="w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  {categories.map((cat) => (
                    <option key={cat.value} value={cat.value}>
                      {cat.label}
                    </option>
                  ))}
                </select>
              </div>

              {/* Urgency */}
              <div className="mb-4">
                <label className="block text-sm font-medium mb-2">
                  Urgency <span className="text-red-400">*</span>
                </label>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  {urgencyLevels.map((level) => (
                    <button
                      key={level.value}
                      type="button"
                      onClick={() => setUrgency(level.value)}
                      className={`px-4 py-3 rounded-lg font-medium transition ${
                        urgency === level.value
                          ? level.color + " text-white"
                          : "bg-slate-800 text-slate-300 hover:bg-slate-700"
                      }`}
                    >
                      {level.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Description */}
              <div className="mb-4">
                <label className="block text-sm font-medium mb-2">
                  Description <span className="text-red-400">*</span>
                </label>
                <textarea
                  required
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  rows={4}
                  className="w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="Detailed description of the problem..."
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading || !title || !description}
              className="w-full py-3 bg-blue-600 hover:bg-blue-500 rounded-lg font-semibold transition disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? "Creating..." : "Continue to Photos"}
            </button>
          </form>
        )}

        {/* Step 2: Photo Upload */}
        {step === 2 && (
          <div className="space-y-6">
            <div className="bg-slate-900 rounded-lg p-6 border border-slate-800">
              <h2 className="text-xl font-semibold mb-4">Add Photos (Optional)</h2>

              {/* Upload Area */}
              <div className="mb-6">
                <label className="block cursor-pointer">
                  <div className="border-2 border-dashed border-slate-700 rounded-lg p-8 text-center hover:border-blue-500 transition">
                    <Upload className="w-12 h-12 mx-auto mb-3 text-slate-400" />
                    <p className="text-slate-300 mb-1">Click to upload or drag and drop</p>
                    <p className="text-sm text-slate-500">PNG, JPG, GIF up to 10MB</p>
                  </div>
                  <input
                    type="file"
                    multiple
                    accept="image/*"
                    onChange={handlePhotoChange}
                    className="hidden"
                  />
                </label>
              </div>

              {/* Photo Previews */}
              {photoPreviews.length > 0 && (
                <div className="grid grid-cols-3 gap-4 mb-4">
                  {photoPreviews.map((preview, index) => (
                    <div key={index} className="relative aspect-square">
                      <img
                        src={preview}
                        alt={`Preview ${index + 1}`}
                        className="w-full h-full object-cover rounded-lg"
                      />
                      <button
                        type="button"
                        onClick={() => removePhoto(index)}
                        className="absolute -top-2 -right-2 p-1 bg-red-600 rounded-full hover:bg-red-500 transition"
                      >
                        <X className="w-4 h-4" />
                      </button>
                    </div>
                  ))}
                </div>
              )}

              {/* Upload Progress */}
              {loading && uploadProgress > 0 && (
                <div className="mb-4">
                  <div className="flex justify-between text-sm mb-2">
                    <span>Uploading...</span>
                    <span>{Math.round(uploadProgress)}%</span>
                  </div>
                  <div className="w-full h-2 bg-slate-800 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-blue-600 transition-all duration-300"
                      style={{ width: `${uploadProgress}%` }}
                    />
                  </div>
                </div>
              )}
            </div>

            {/* Action Buttons */}
            <div className="flex gap-4">
              <button
                type="button"
                onClick={handleSkipPhotos}
                disabled={loading}
                className="flex-1 py-3 bg-slate-800 hover:bg-slate-700 rounded-lg font-semibold transition disabled:opacity-50"
              >
                Skip Photos
              </button>
              <button
                type="button"
                onClick={handlePhotoSubmit}
                disabled={loading || photos.length === 0}
                className="flex-1 py-3 bg-blue-600 hover:bg-blue-500 rounded-lg font-semibold transition disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? "Uploading..." : `Continue (${photos.length} ${photos.length === 1 ? "photo" : "photos"})`}
              </button>
            </div>
          </div>
        )}

        {/* Step 3: Discovery Questions */}
        {step === 3 && (
          <form onSubmit={handleDiscoverySubmit} className="space-y-6">
            <div className="bg-slate-900 rounded-lg p-6 border border-slate-800">
              <h2 className="text-xl font-semibold mb-4">Additional Details</h2>

              {discoveryQuestions[category].map((question, index) => (
                <div key={index} className="mb-4">
                  <label className="block text-sm font-medium mb-2">{question}</label>
                  <textarea
                    value={answers[question] || ""}
                    onChange={(e) =>
                      setAnswers((prev) => ({ ...prev, [question]: e.target.value }))
                    }
                    rows={3}
                    className="w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="Your answer..."
                  />
                </div>
              ))}
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 bg-emerald-600 hover:bg-emerald-500 rounded-lg font-semibold transition disabled:opacity-50"
            >
              {loading ? "Submitting..." : "Submit Incident Report"}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
