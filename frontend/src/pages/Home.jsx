import React, { useState } from 'react';
import Navbar from '../components/Navbar';
export default function Home() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-white to-slate-50 text-slate-900 font-sans">
      {/* Top nav */}
      <main className="max-w-7xl mx-auto px-8 py-20">
        {/* HERO */}
        <section className="grid grid-cols-1 md:grid-cols-2 gap-10 items-center">
          <div>
            <p className="text-2xl  font-bold text-sky-700 inline-flex items-center gap-2 px-8"> 
              {/* <svg width="16" height="16" viewBox="0 0 24 24" fill="none"><path d="M12 2v6" stroke="#0ea5e9" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/></svg> */}
              Real-time emergency guidance
            </p>
            <h2 className="mt-2 text-3xl sm:text-4xl font-extrabold leading-tight">
              Aurora: Instant AI Field Assistant for Emergencies
            </h2>
            <p className="mt-4 text-slate-600 max-w-xl px-8">
              Real-time guidance for frontline workers — safety without delay. Clear SOPs, automated alerts, and supervisor oversight when it matters most.
            </p>
            
            <div className="mt-6 grid grid-cols-3 gap-6">
            <div>
                <div className="text-3xl font-bold text-sky-700 mb-1">&lt;500ms</div>
                <div className="text-sm text-gray-600">Response Time</div>
            </div>
            <div>
                <div className="text-3xl font-bold text-sky-700 mb-1">24/7</div>
                <div className="text-sm text-gray-600">Always Available</div>
            </div>
            <div>
                <div className="text-3xl font-bold text-sky-700 mb-1">100%</div>
                <div className="text-sm text-gray-600">Logged</div>
            </div>
            </div>
            <div className="mt-6 flex flex-wrap justify-center gap-3">
              <a href='https://aurora-as.onrender.com/web-call' className="px-5 py-3 rounded-md bg-sky-700 text-white font-semibold shadow-md hover:brightness-95">Demo</a>
              <a className="px-5 py-3 rounded-md border border-slate-200 text-slate-800 font-medium" href='#howitworks'>How It Works</a>
            </div>
          </div>
          

          {/* Hero visual: split: left shows field worker + abstract network */}
          <div className="relative">
            <div className="rounded-2xl border border-slate-100 shadow-lg overflow-hidden">
              <div className="bg-gradient-to-b from-slate-800/80 to-slate-900/90 p-6 text-white">
                <div className="flex items-center justify-between">
                  <div className='flex flex-col justify-start items-start'>
                    <div className="text-xs uppercase tracking-wide text-red-600 font-bold">Live · Emergency</div>
                    <div className=" text-lg font-bold">Zone B — Gas Leak Alert</div>
                  </div>
                  <div className="text-right">
                    <div className="text-xs text-slate-300">ETA responders</div>
                    <div className="text-sm font-semibold">3m 12s</div>
                  </div>
                </div>
              </div>

              <div className="p-6 bg-white">
                <div className="flex items-center gap-4">
                  <div className="w-12 h-12 rounded-md bg-orange-50 flex items-center justify-center border border-orange-100">
                    {/* worker icon */}
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none"><path d="M12 2v6" stroke="#fb923c" strokeWidth="1.6" strokeLinecap="round"/></svg>
                  </div>
                  <div>
                    <div className="text-sm font-semibold">Field Worker</div>
                    <div className="text-xs text-slate-500">Valve 3 — Zone B</div>
                  </div>
                </div>

                <div className="mt-5 border rounded-lg p-4 bg-slate-50">
                  <div className="text-sm text-slate-700">"Strong smell of gas near Valve 3"</div>
                  <div className="mt-3 text-xs text-slate-500">Sent via voice → transcribed</div>
                </div>

                <div className="mt-4 grid grid-cols-2 gap-3">
                  <div className="p-3 rounded-md border border-slate-100">
                    <div className="text-xs uppercase text-slate-500">Action</div>
                    <div className="mt-2 font-semibold">Evacuate Zone B</div>
                  </div>
                  <div className="p-3 rounded-md border border-slate-100">
                    <div className="text-xs uppercase text-slate-500">Notify</div>
                    <div className="mt-2 font-semibold text-amber-600">Responders & Supervisors</div>
                  </div>
                </div>

                <div className="mt-4 flex items-center justify-between">
                  <div className="text-xs text-slate-500">Logged · Incident ID #A-2025-321</div>
                  <div className="text-sm font-semibold text-sky-700">View details</div>
                </div>
              </div>
            </div>

            {/* subtle background abstract vector */}
            <svg className="absolute -right-6 -top-8 opacity-30" width="220" height="220" viewBox="0 0 220 220" fill="none" xmlns="http://www.w3.org/2000/svg">
              <defs>
                <linearGradient id="g1" x1="0" x2="1">
                  <stop offset="0" stopColor="#0ea5e9" stopOpacity="0.6"/>
                  <stop offset="1" stopColor="#fb923c" stopOpacity="0.6"/>
                </linearGradient>
              </defs>
              <circle cx="110" cy="110" r="80" stroke="url(#g1)" strokeWidth="2"/>
              <path d="M30 110h160M110 30v160" stroke="url(#g1)" strokeWidth="1" strokeLinecap="round" />
            </svg>
          </div>
        </section>
        
        {/* HOW IT WORKS */}
        <section className="mt-10 bg-gradient-to-b from-white to-slate-50 p-6 rounded-2xl border border-slate-100" id='howitworks'>
          <div className="max-w-4xl mx-auto mt-15">
            <h3 className="text-4xl font-bold">How it works</h3>
            <p className="mt-2 text-slate-600">Simple, low-friction flow so workers get actionable guidance in seconds.</p>

            <div className="mt-6 grid grid-cols-1 md:grid-cols-3 gap-6">
              <StepCard
                title="1. Worker reports issue"
                desc="Voice, chat or telegram — quick inputs from the field."
                icon={<WorkerIcon />}
              />

              <StepCard
                title="2. Aurora provides SOPs"
                desc="Clear, safety-first steps delivered instantly."
                icon={<AssistantIcon />}
              />

              <StepCard
                title="3. Alerts & logs"
                desc="Automatic responder alerts and archived logs for supervisors."
                icon={<SupervisorIcon />}
              />
            </div>
          </div>
        </section>
        <section className='m-10 flex gap-12 w-full'>
            <div className="bg-white rounded-2xl shadow-2xl overflow-hidden w-[45%]">
              <div className="bg-gradient-to-r from-gray-800 to-gray-900 px-6 py-4">
                <h3 className="font-bold text-white text-lg">Supervisor Dashboard</h3>
                <p className="text-sm text-gray-300">Real-time monitoring & control</p>
              </div>

              <div className="p-6 space-y-4">
                <div className="border-l-4 border-red-600 bg-red-50 p-4 rounded-r-lg">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-bold text-red-600 uppercase">Critical</span>
                    <span className="text-xs text-gray-500">2 mins ago</span>
                  </div>
                  <p className="font-semibold text-gray-900 mb-1">Gas Leak - Zone B</p>
                  <p className="text-sm text-gray-600 mb-3">Worker: John Martinez | ID: #2847</p>
                  <button className="w-full px-4 py-2 bg-red-600 text-white rounded-lg font-semibold hover:bg-red-700 transition text-sm">
                    Take Over Conversation
                  </button>
                </div>

                <div className="border-l-4 border-yellow-500 bg-yellow-50 p-4 rounded-r-lg">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-bold text-yellow-600 uppercase">Monitoring</span>
                    <span className="text-xs text-gray-500">15 mins ago</span>
                  </div>
                  <p className="font-semibold text-gray-900 mb-1">Equipment Malfunction</p>
                  <p className="text-sm text-gray-600">Worker: Sarah Chen | ID: #2846</p>
                </div>

                <div className="border-l-4 border-green-500 bg-green-50 p-4 rounded-r-lg">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-bold text-green-600 uppercase">Resolved</span>
                    <span className="text-xs text-gray-500">1 hour ago</span>
                  </div>
                  <p className="font-semibold text-gray-900 mb-1">Safety Check Complete</p>
                  <p className="text-sm text-gray-600">Worker: Mike Torres | ID: #2845</p>
                </div>

                <div className="bg-gray-100 p-4 rounded-lg">
                  <div className="flex items-center space-x-2 text-gray-700 mb-2">
                    <span className="font-semibold">Compliance Archive</span>
                  </div>
                  <p className="text-sm text-gray-600">All conversations logged and searchable for audits</p>
                </div>
              </div>
            </div>
            {/* <h3 className="text-xl font-bold">Worker Chat Interface</h3> */}
            <div className="bg-white rounded-2xl shadow-2xl overflow-hidden w-[45%]">
              <div className="bg-gradient-to-r from-blue-700 to-blue-800 px-6 py-4 flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <div className="w-10 h-10 bg-white/20 rounded-full flex items-center justify-center">
                    {/* <Shield className="w-6 h-6 text-white" /> */}
                  </div>
                  <div className='flex-col justify-start items-start'>
                    <div className="font-bold text-white">Aurora AI Assistant for Workers</div>
                    <div className="text-xs text-blue-100 flex items-start">Active - Monitoring</div>
                  </div>
                </div>
                <div className="w-3 h-3 bg-green-400 rounded-full animate-pulse"></div>
              </div>

              <div className="p-6 space-y-4 h-120 overflow-y-auto bg-gray-50">
                {/* Worker Message */}
                <div className="flex justify-end">
                  <div className="bg-blue-600 text-white rounded-2xl rounded-tr-sm px-5 py-3 max-w-xs">
                    <p className="text-sm font-medium">Strong smell of gas in Zone B near Valve 3.</p>
                    <p className="text-xs text-blue-200 mt-1">14:32</p>
                  </div>
                </div>

                {/* Aurora Critical Response */}
                <div className="flex justify-start">
                  <div className="bg-red-600 text-white rounded-2xl rounded-tl-sm px-5 py-3 max-w-sm border-2 border-red-700">
                    <div className="flex items-center space-x-2 mb-2">
                      {/* <AlertCircle className="w-4 h-4" /> */}
                      <span className="text-xs font-bold uppercase">Critical Alert</span>
                    </div>
                    <p className="text-sm font-bold mb-2">EVACUATE Zone B immediately</p>
                    <p className="text-sm leading-relaxed">Emergency protocol activated. Follow these steps:</p>
                    <ol className="text-sm mt-2 space-y-1 list-decimal list-inside">
                      <li>Sound evacuation alarm</li>
                      <li>Move upwind to Assembly Point 2</li>
                      <li>Account for all personnel</li>
                      <li>Do not re-enter until cleared</li>
                    </ol>
                    <p className="text-xs text-red-200 mt-2">14:32</p>
                  </div>
                </div>

                {/* System Notification */}
                <div className="bg-yellow-100 border-l-4 border-yellow-500 p-4 rounded">
                  <div className="flex items-start space-x-2">
                    {/* <CheckCircle className="w-5 h-5 text-yellow-600 mt-0.5" /> */}
                    <div className="text-sm text-yellow-800">
                      <p className="font-semibold">Automatic actions taken:</p>
                      <ul className="mt-1 space-y-1">
                        <li>✓ Emergency team notified</li>
                        <li>✓ Supervisor alerted</li>
                        <li>✓ Incident logged (ID: #2847)</li>
                      </ul>
                    </div>
                  </div>
                </div>
              </div>

              <div className="bg-white px-6 py-4 border-t border-gray-200">
                <div className="flex items-center space-x-3">
                  <input 
                    type="text" 
                    placeholder="Type or use voice..."
                    className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                    disabled
                  />
                  <button className="w-10 h-10 bg-blue-600 rounded-lg flex items-center justify-center text-white">
                    {/* <MessageSquare className="w-5 h-5" /> */}
                  </button>
                </div>
              </div>
            </div>
        </section>
        

        {/* Why Aurora Helps */}
        <section className="mt-20" id='usecase'> 
          <h3 className="text-4xl font-bold p-4">Why Aurora helps</h3>
          <div className="mt-4 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <FeatureCard title="Faster response" desc="Reduce decision time with instant SOPs." icon="⚡" />
            <FeatureCard title="Automatic alerts" desc="Immediate notifications to responders." icon="🚨" />
            <FeatureCard title="Supervisor control" desc="Take over incidents with a single click." icon="👤" />
            <FeatureCard title="Logged history" desc="Immutable logs for audits & compliance." icon="📜" />
          </div>
        </section>

        {/* CTA Banner */}
        <section className="mt-12 rounded-2xl bg-gradient-to-r from-sky-700 to-indigo-700 text-white p-6 flex flex-col md:flex-row items-center justify-between">
          <div>
            <h4 className="text-lg font-bold">Bring Aurora to your frontline teams — safety in seconds.</h4>
            <p className="mt-1 text-sm opacity-90">Book a demo to see how Aurora integrates with your incident workflows.</p>
          </div>
          <div className="mt-4 md:mt-0 flex gap-3">
            <button className="px-5 py-3 rounded-md bg-white text-sky-700 font-semibold">Request a Demo</button>
            <button className="px-5 py-3 rounded-md border border-white text-white">Contact Sales</button>
          </div>
        </section>

        <footer className="mt-12 text-sm text-slate-500">
          <div className="flex flex-col md:flex-row items-center justify-between gap-3">
            <div>© {new Date().getFullYear()} Aurora — AI Field Assistant · All rights reserved.</div>
            <div className="flex gap-4">
              <div>Privacy</div>
              <div>Security</div>
              <div>Docs</div>
            </div>
          </div>
        </footer>
      </main>
    </div>
  );
}


/* ----------------- Small helper components (in-file) ----------------- */

function StepCard({ title, desc, icon }) {
  return (
    <div className="p-4 bg-white rounded-lg border border-slate-100 shadow-sm">
      <div className="flex items-center gap-3">
        <div className="w-12 h-12 rounded-md bg-slate-50 flex items-center justify-center">{icon}</div>
        <div>
          <div className="font-semibold">{title}</div>
          <div className="text-sm text-slate-500">{desc}</div>
        </div>
      </div>
    </div>
  );
}

function MessageBubble({ from = "aurora", text = "", highlight = false }) {
  const isAurora = from === "aurora";
  return (
    <div className={`${isAurora ? 'self-start' : 'self-end'} flex flex-col max-w-prose`}>
      <div className={`${isAurora ? 'bg-slate-50 border border-slate-100' : 'bg-sky-700 text-white'} p-3 rounded-lg whitespace-pre-line ${highlight ? 'ring-2 ring-amber-200' : ''}`}>
        <div className={`text-sm ${isAurora ? 'text-slate-800' : 'text-white'}`}>{text}</div>
      </div>
    </div>
  );
}

function FeatureCard({ title, desc, icon }) {
  return (
    <div className="p-4 bg-white rounded-lg border border-slate-100 shadow-sm flex items-start gap-3">
      <div className="text-2xl my-auto">{icon}</div>
      <div>
        <div className="font-semibold">{title}</div>
        <div className="text-sm text-slate-500">{desc}</div>
      </div>
    </div>
  );
}


/* Simple SVG icons */
function WorkerIcon() {
  return (
    <svg width="28" height="28" viewBox="0 0 24 24" fill="none">
      <rect x="3" y="3" width="18" height="18" rx="4" fill="#fff" />
      <path d="M8 15c0-2.2 1.8-4 4-4s4 1.8 4 4" stroke="#0ea5e9" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx="12" cy="8" r="2" stroke="#0ea5e9" strokeWidth="1.6" />
    </svg>
  );
}

function AssistantIcon() {
  return (
    <svg width="28" height="28" viewBox="0 0 24 24" fill="none">
      <rect x="3" y="3" width="18" height="18" rx="4" fill="#fff" />
      <path d="M7 13h10M7 17h6" stroke="#fb923c" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M12 7v0" stroke="#fb923c" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function SupervisorIcon() {
  return (
    <svg width="28" height="28" viewBox="0 0 24 24" fill="none">
      <rect x="3" y="3" width="18" height="18" rx="4" fill="#fff" />
      <path d="M8 12h8M8 16h5" stroke="#10b981" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx="12" cy="8" r="1.5" stroke="#10b981" strokeWidth="1.6" />
    </svg>
  );
}


// export default Home;