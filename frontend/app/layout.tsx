import '../src/app/globals.css'
import { ReactNode } from 'react'

export const metadata = {
  title: 'LandTen Contractor & Landlord Flows',
  description: 'Legacy app directory routes for contractor and landlord flows',
}

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-slate-950 text-slate-100">
        {children}
      </body>
    </html>
  )
}
