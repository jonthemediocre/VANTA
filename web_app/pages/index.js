import { useState } from 'react'

export default function Home() {
  const [input, setInput] = useState("")
  const [resp, setResp] = useState("Awaiting input...")
  const [isLoading, setIsLoading] = useState(false)

  const sendPrompt = async () => {
    if (!input.trim()) {
      setResp("Please enter a prompt.");
      return;
    }
    setIsLoading(true);
    setResp("Sending prompt to VANTA-SEED...");
    try {
      const r = await fetch('/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ prompt: input })
      });
      
      if (!r.ok) {
          const errorData = await r.json().catch(() => ({ detail: "Unknown server error" }));
          throw new Error(errorData.detail || `HTTP error! status: ${r.status}`);
      }
      
      const data = await r.json();
      setResp(data.reply || "No reply received.");
      
    } catch (error) {
       console.error("Fetch error:", error);
       setResp(`Error: ${error.message}`);
    } finally {
       setIsLoading(false);
    }
  }

  return (
    // Basic Tailwind styling assumes Tailwind is set up in the Next.js project
    <div className="p-4 max-w-2xl mx-auto font-sans">
      <h1 className="text-2xl font-bold mb-4 text-center text-gray-700">VANTA-SEED Console</h1>
      <textarea
        className="w-full h-32 p-2 border border-gray-300 rounded shadow-sm focus:ring-blue-500 focus:border-blue-500"
        value={input}
        onChange={e => setInput(e.target.value)}
        placeholder="Enter your prompt for VANTA-SEED..."
        disabled={isLoading}
      />
      <button
        className={`mt-2 px-4 py-2 w-full font-semibold text-white rounded transition-colors duration-150 ${isLoading ? 'bg-gray-400 cursor-not-allowed' : 'bg-blue-600 hover:bg-blue-700'}`}
        onClick={sendPrompt}
        disabled={isLoading}
      >
        {isLoading ? 'Processing...' : 'Send Prompt'}
      </button>
      <h2 className="mt-6 text-xl font-semibold text-gray-600">Response:</h2>
      <pre className="mt-2 bg-gray-100 p-3 border border-gray-200 rounded whitespace-pre-wrap break-words min-h-[50px] text-gray-800">
        {resp}
      </pre>
    </div>
  )
} 