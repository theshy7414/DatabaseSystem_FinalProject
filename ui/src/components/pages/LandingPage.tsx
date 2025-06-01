import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";

export default function LandingPage() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-gray-100 flex items-center justify-center">
      <div className="max-w-2xl mx-auto px-4 text-center">
        <h1 className="text-5xl font-bold mb-6 text-gray-900">
          Your Personal Fashion Assistant
        </h1>
        <p className="text-xl text-gray-600 mb-8">
          Get personalized fashion recommendations and style advice powered by AI
        </p>
        <Button
          size="lg"
          onClick={() => navigate("/chat")}
          className="bg-blue-600 text-white hover:bg-blue-700 px-8 py-3 text-lg font-semibold shadow-lg"
        >
          Start Chatting
        </Button>
      </div>
    </div>
  );
} 