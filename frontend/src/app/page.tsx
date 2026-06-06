import { ChatApp } from "@/components/ChatApp";
import { DisclaimerFooter } from "@/components/DisclaimerFooter";
import { Header } from "@/components/Header";

export default function Home() {
  return (
    <div className="flex min-h-screen flex-col bg-[#0B1120] font-sans text-slate-100">
      <Header />
      <ChatApp />
      <DisclaimerFooter />
    </div>
  );
}
