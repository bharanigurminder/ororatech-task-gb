import './globals.css'

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className="bg-gray-50 min-h-screen">
        <div className="min-h-screen flex flex-col">
          <header className="bg-white shadow-sm border-b">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
              <div className="flex justify-between items-center py-4">
                <div className="flex items-center space-x-4">
                  <div className="w-8 h-8 bg-green-600 rounded-full flex items-center justify-center">
                    <span className="text-white font-bold text-sm">🗺️</span>
                  </div>
                  <div>
                    <h1 className="text-xl font-semibold text-gray-900">Fuel Map Integration</h1>
                    <p className="text-sm text-gray-500">Geospatial Fuel Data Processing Platform</p>
                  </div>
                </div>
                <div className="flex items-center space-x-2">
                  <div className="text-xs text-gray-500">
                    <span className="w-2 h-2 bg-green-400 rounded-full inline-block mr-1"></span>
                    Phase 1+2+3 Active
                  </div>
                </div>
              </div>
            </div>
          </header>

          <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
            {children}
          </main>

          <footer className="bg-white border-t mt-8">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
              <p className="text-sm text-gray-500 text-center">
                Fuel Map Integration Platform - Phase 3 Frontend
              </p>
            </div>
          </footer>
        </div>
      </body>
    </html>
  )
}