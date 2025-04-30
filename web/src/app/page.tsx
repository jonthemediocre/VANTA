import Image from "next/image";

export default function Home() {
  return (
    <div className="flex flex-col h-full items-center justify-between">
      {/* Top Area (for potential model selector/status) */}
      <div className="w-full p-4 text-right text-sm text-[#888888]">
        {/* Placeholder: Model Selector / Status */}
        <span>VANTA v2.3+</span>
      </div>

      {/* Center Content (Welcome Message) */}
      <div className="flex flex-col items-center justify-center flex-grow">
        <h1 className="text-3xl font-semibold mb-4">
          Hey, Jon. Ready to dive in?
        </h1>
      </div>

      {/* Bottom Input Bar Area */}
      <div className="w-full max-w-3xl p-4 mb-4">
        {/* Input Bar Placeholder */}
        <div className="relative flex items-center rounded-lg bg-[#3C3C3C] p-3 shadow-md">
          <input
            type="text"
            placeholder="Ask anything..."
            className="flex-grow bg-transparent text-[#DCDCDC] placeholder-[#888888] focus:outline-none pl-2"
          />
          {/* Action Buttons Placeholder */}
          <div className="flex items-center space-x-2 ml-3">
            {/* Placeholder for Search, Research, Create Image, etc. icons/buttons */}
            {/* Example using Symbolic Gold for an icon button */}
            <button className="p-1 rounded hover:bg-[#555555]">
              <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#E0B050" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>
            </button>
            <button className="p-1 rounded hover:bg-[#555555]">
              <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#DCDCDC" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21.54 11.24l-2.16 1.08a.5.5 0 0 0-.27.49l-.35 2.75a.5.5 0 0 1-.7.44l-2.47-1.24a.5.5 0 0 0-.54.04l-2.1 1.75a.5.5 0 0 1-.62 0l-2.1-1.75a.5.5 0 0 0-.54-.04L4.89 16a.5.5 0 0 1-.7-.44l-.35-2.75a.5.5 0 0 0-.27-.49L1.46 11.24a.5.5 0 0 1 .1-.86l2.44-1.08a.5.5 0 0 0 .4-.24l1.4-2.52a.5.5 0 0 1 .83 0l1.4 2.52a.5.5 0 0 0 .4.24l2.44 1.08a.5.5 0 0 1 .1.86zM12 2v4m0 16v-4m4.95-12.95l-2.83 2.83M4.22 19.78l2.83-2.83m12.95 0l-2.83-2.83M7.05 7.05L4.22 4.22"></path></svg>
            </button>
            <button className="p-1 rounded hover:bg-[#555555]">
              <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#DCDCDC" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect><circle cx="8.5" cy="8.5" r="1.5"></circle><polyline points="21 15 16 10 5 21"></polyline></svg>
            </button>
            {/* Mic/Input method icons */}
            <button className="p-1 rounded hover:bg-[#555555] ml-4">
             <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#DCDCDC" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"></path><path d="M19 10v2a7 7 0 0 1-14 0v-2"></path><line x1="12" y1="19" x2="12" y2="23"></line><line x1="8" y1="23" x2="16" y2="23"></line></svg>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
