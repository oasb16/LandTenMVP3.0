export const productionConfig = {
  apiUrl: 'https://landtenmvp3-55ce0053f28a.herokuapp.com/api/v1',
  stripePublishableKey: process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY!,
  frontendUrl: 'https://land-ten-mvp-3-0.vercel.app',
  enableAnalytics: true,
  enableErrorTracking: true,
  environment: 'production',
}

export async function apiRequest(endpoint: string, options: RequestInit = {}) {
  const response = await fetch(`${productionConfig.apiUrl}${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  })

  if (!response.ok) {
    throw new Error(`API error: ${response.statusText}`)
  }

  return response.json()
}
