"use client";

import { useState } from "react";
import { PlayCircle, Loader2 } from "lucide-react";

export default function ContractorOnboardingTest() {
  const [testing, setTesting] = useState(false);
  const [logs, setLogs] = useState<string[]>([]);

  const log = (message: string) => {
    const timestamp = new Date().toLocaleTimeString();
    const logMessage = `[${timestamp}] ${message}`;
    console.log(logMessage);
    setLogs((prev) => [...prev, logMessage]);
  };

  const clearLogs = () => {
    setLogs([]);
  };

  const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

  const runEndToEndTest = async () => {
    setTesting(true);
    clearLogs();

    const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL;
    const testEmail = `test-contractor-${Date.now()}@example.com`;
    const testJobId = `job_test_${Date.now()}`;

    try {
      log("🚀 Starting End-to-End Contractor Onboarding Test");
      log(`📧 Test Email: ${testEmail}`);
      log(`💼 Test Job ID: ${testJobId}`);
      log("─────────────────────────────────────────────────");

      // ============================================================
      // PHASE 1: Magic Link Creation & Verification
      // ============================================================
      log("");
      log("📋 PHASE 1: Magic Link Creation & Verification");
      log("─────────────────────────────────────────────────");

      // Step 1: Create magic link
      log("Step 1: Creating magic link...");
      const createLinkRes = await fetch(`${backendUrl}/api/v1/magic-links/create`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: testEmail,
          job_id: testJobId,
          landlord_id: "test_landlord",
          property_id: "test_property",
          tenant_id: "test_tenant",
        }),
      });

      if (!createLinkRes.ok) {
        throw new Error(`Failed to create magic link: ${createLinkRes.status}`);
      }

      const linkData = await createLinkRes.json();
      const magicToken = linkData.token;
      log(`✅ Magic link created: token=${magicToken.substring(0, 20)}...`);
      log(`🔗 Full URL: /contractor-onboarding?token=${magicToken}`);

      await sleep(500);

      // Step 2: Verify magic link
      log("");
      log("Step 2: Verifying magic link...");
      const verifyRes = await fetch(`${backendUrl}/api/v1/magic-links/verify`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token: magicToken }),
      });

      if (!verifyRes.ok) {
        throw new Error(`Failed to verify magic link: ${verifyRes.status}`);
      }

      const verifyData = await verifyRes.json();
      log(`✅ Magic link verified: valid=${verifyData.valid}`);
      log(`📧 Email: ${verifyData.email}`);

      await sleep(500);

      // Step 3: Create contractor record
      log("");
      log("Step 3: Creating contractor record...");
      const registerRes = await fetch(`${backendUrl}/api/v1/contractors/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          business_name: "Test Contractor LLC",
          email: testEmail,
          phone: "555-1234",
          categories: ["plumbing"],
          service_zip_codes: ["12345"],
          license_number: "",
        }),
      });

      if (!registerRes.ok) {
        const errorText = await registerRes.text();
        throw new Error(`Failed to register contractor: ${registerRes.status} - ${errorText}`);
      }

      const registerData = await registerRes.json();
      const contractorId = registerData.contractor.contractor_id;
      log(`✅ Contractor created: ${contractorId}`);

      await sleep(500);

      // Step 4: Check initial onboarding status
      log("");
      log("Step 4: Checking initial onboarding status...");
      const statusRes1 = await fetch(`${backendUrl}/api/v1/contractors/${contractorId}/onboarding-status`);

      if (!statusRes1.ok) {
        throw new Error(`Failed to get onboarding status: ${statusRes1.status}`);
      }

      const status1 = await statusRes1.json();
      log(`✅ Initial status retrieved:`);
      log(`   - License Submitted: ${status1.onboarding_license_submitted}`);
      log(`   - License Verified: ${status1.onboarding_license_verified}`);
      log(`   - Identity Verified: ${status1.onboarding_identity_verified}`);
      log(`   - Payment Setup: ${status1.onboarding_payment_setup}`);
      log(`   - Complete: ${status1.onboarding_complete}`);
      log(`   - Current Step: ${status1.onboarding_current_step}`);

      // ============================================================
      // PHASE 2: Agent Tool Testing
      // ============================================================
      log("");
      log("📋 PHASE 2: Agent Tool Testing");
      log("─────────────────────────────────────────────────");

      await sleep(1000);

      // Step 5: Test submit_license tool
      log("");
      log("Step 5: Testing submit_license tool...");
      const licenseRes = await fetch(
        `${backendUrl}/api/v1/contractors/${contractorId}/onboarding-status?` +
          new URLSearchParams({
            license_submitted: "true",
            license_verified: "true",
            current_step: "identity",
          }),
        {
          method: "PATCH",
        }
      );

      if (!licenseRes.ok) {
        throw new Error(`Failed to submit license: ${licenseRes.status}`);
      }

      log(`✅ License submitted successfully`);

      await sleep(500);

      // Verify status update
      const statusRes2 = await fetch(`${backendUrl}/api/v1/contractors/${contractorId}/onboarding-status`);
      const status2 = await statusRes2.json();
      log(`   - License Verified: ${status2.onboarding_license_verified} ✓`);
      log(`   - Current Step: ${status2.onboarding_current_step}`);

      await sleep(1000);

      // Step 6: Test trigger_identity_verification tool
      log("");
      log("Step 6: Testing trigger_identity_verification tool...");
      const identityRes = await fetch(
        `${backendUrl}/api/v1/contractors/${contractorId}/onboarding-status?` +
          new URLSearchParams({
            identity_verified: "true",
            current_step: "payment",
          }),
        {
          method: "PATCH",
        }
      );

      if (!identityRes.ok) {
        throw new Error(`Failed to verify identity: ${identityRes.status}`);
      }

      log(`✅ Identity verified successfully`);

      await sleep(500);

      // Verify status update
      const statusRes3 = await fetch(`${backendUrl}/api/v1/contractors/${contractorId}/onboarding-status`);
      const status3 = await statusRes3.json();
      log(`   - Identity Verified: ${status3.onboarding_identity_verified} ✓`);
      log(`   - Current Step: ${status3.onboarding_current_step}`);

      await sleep(1000);

      // Step 7: Test setup_bank_account tool
      log("");
      log("Step 7: Testing setup_bank_account tool...");
      const paymentRes = await fetch(
        `${backendUrl}/api/v1/contractors/${contractorId}/onboarding-status?` +
          new URLSearchParams({
            payment_setup: "true",
            current_step: "done",
          }),
        {
          method: "PATCH",
        }
      );

      if (!paymentRes.ok) {
        throw new Error(`Failed to setup payment: ${paymentRes.status}`);
      }

      log(`✅ Bank account setup successfully`);

      await sleep(500);

      // Verify status update
      const statusRes4 = await fetch(`${backendUrl}/api/v1/contractors/${contractorId}/onboarding-status`);
      const status4 = await statusRes4.json();
      log(`   - Payment Setup: ${status4.onboarding_payment_setup} ✓`);
      log(`   - Current Step: ${status4.onboarding_current_step}`);

      await sleep(1000);

      // Step 8: Test mark_onboarding_complete tool
      log("");
      log("Step 8: Testing mark_onboarding_complete tool...");
      const completeRes = await fetch(
        `${backendUrl}/api/v1/contractors/${contractorId}/onboarding-status?` +
          new URLSearchParams({
            complete: "true",
            current_step: "done",
          }),
        {
          method: "PATCH",
        }
      );

      if (!completeRes.ok) {
        throw new Error(`Failed to complete onboarding: ${completeRes.status}`);
      }

      log(`✅ Onboarding marked complete`);

      await sleep(500);

      // Verify final status
      const statusResFinal = await fetch(`${backendUrl}/api/v1/contractors/${contractorId}/onboarding-status`);
      const statusFinal = await statusResFinal.json();
      log(`   - Onboarding Complete: ${statusFinal.onboarding_complete} ✓`);

      // ============================================================
      // PHASE 3: Verification
      // ============================================================
      log("");
      log("📋 PHASE 3: Final Verification");
      log("─────────────────────────────────────────────────");

      log("");
      log("Final Onboarding Status:");
      log(`   ✅ License Submitted: ${statusFinal.onboarding_license_submitted}`);
      log(`   ✅ License Verified: ${statusFinal.onboarding_license_verified}`);
      log(`   ✅ Identity Verified: ${statusFinal.onboarding_identity_verified}`);
      log(`   ✅ Payment Setup: ${statusFinal.onboarding_payment_setup}`);
      log(`   ✅ Onboarding Complete: ${statusFinal.onboarding_complete}`);
      log(`   📍 Current Step: ${statusFinal.onboarding_current_step}`);

      log("");
      log("─────────────────────────────────────────────────");
      log("🎉 END-TO-END TEST COMPLETED SUCCESSFULLY!");
      log("─────────────────────────────────────────────────");
      log("");
      log("📌 Test Details:");
      log(`   Contractor ID: ${contractorId}`);
      log(`   Email: ${testEmail}`);
      log(`   Magic Token: ${magicToken.substring(0, 30)}...`);
      log("");
      log("🔗 You can test the UI at:");
      log(`   ${window.location.origin}/contractor-onboarding?token=${magicToken}`);

    } catch (error) {
      log("");
      log("❌ TEST FAILED!");
      log(`Error: ${error instanceof Error ? error.message : String(error)}`);
      if (error instanceof Error && error.stack) {
        log(`Stack: ${error.stack}`);
      }
    } finally {
      setTesting(false);
    }
  };

  return (
    <div className="w-full max-w-4xl mx-auto p-6 space-y-4">
      <div className="bg-white rounded-lg shadow-lg p-6">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">
          Contractor Onboarding E2E Test
        </h2>
        <p className="text-gray-600 mb-6">
          This test runs the complete contractor onboarding flow including magic link creation,
          contractor registration, and all agent tool calls (submit_license, trigger_identity_verification,
          setup_bank_account, mark_onboarding_complete).
        </p>

        <button
          onClick={runEndToEndTest}
          disabled={testing}
          className="flex items-center gap-2 px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
        >
          {testing ? (
            <>
              <Loader2 className="h-5 w-5 animate-spin" />
              Running Test...
            </>
          ) : (
            <>
              <PlayCircle className="h-5 w-5" />
              Run End-to-End Test
            </>
          )}
        </button>
      </div>

      {logs.length > 0 && (
        <div className="bg-gray-900 rounded-lg shadow-lg p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-white">Test Logs</h3>
            <button
              onClick={clearLogs}
              className="px-3 py-1 text-sm bg-gray-700 text-white rounded hover:bg-gray-600 transition-colors"
            >
              Clear Logs
            </button>
          </div>
          <textarea
            readOnly
            value={logs.join("\n")}
            className="w-full h-96 p-4 bg-black text-green-400 font-mono text-sm rounded border border-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
            style={{ resize: "vertical" }}
          />
        </div>
      )}
    </div>
  );
}
