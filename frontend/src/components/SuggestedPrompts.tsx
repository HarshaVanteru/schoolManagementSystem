import React from "react";
import { Sparkles, Users, Award, BookOpen, Layers } from "lucide-react";

interface SuggestedPromptsProps {
  onSelectPrompt: (prompt: string) => void;
}

const PROMPTS = [
  {
    icon: Users,
    title: "All Students",
    prompt: "Show all students with their class and roll numbers",
  },
  {
    icon: Award,
    title: "Top Performers",
    prompt: "Show the top 5 students by total marks in recent exams",
  },
  {
    icon: Layers,
    title: "Class Breakdown",
    prompt: "List all classes with total student count in each",
  },
  {
    icon: BookOpen,
    title: "Exam Marks",
    prompt: "Show marks obtained by students in Mathematics exam",
  },
];

export const SuggestedPrompts: React.FC<SuggestedPromptsProps> = ({
  onSelectPrompt,
}) => {
  return (
    <div className="py-8 px-4 flex flex-col items-center justify-center text-center max-w-xl mx-auto">
      <div className="w-12 h-12 rounded-2xl bg-gradient-to-tr from-blue-600/20 to-indigo-600/20 border border-blue-500/20 flex items-center justify-center mb-4 text-blue-400">
        <Sparkles className="w-6 h-6" />
      </div>
      <h2 className="text-xl font-semibold text-zinc-100 tracking-tight">
        How can I assist you today?
      </h2>
      <p className="text-sm text-zinc-400 mt-1.5 max-w-md">
        Ask anything regarding students, exam scores, classes, or teachers.
        The AI generates and executes SQL queries in real-time.
      </p>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 mt-8 w-full text-left">
        {PROMPTS.map((item, index) => {
          const Icon = item.icon;
          return (
            <button
              key={index}
              onClick={() => onSelectPrompt(item.prompt)}
              className="group p-3 rounded-xl bg-zinc-900/50 hover:bg-zinc-800/80 border border-zinc-800 hover:border-zinc-700 transition-all text-left flex items-start space-x-3 shadow-sm hover:shadow-md"
            >
              <div className="p-2 rounded-lg bg-zinc-800/80 group-hover:bg-blue-500/20 text-zinc-400 group-hover:text-blue-400 transition-colors">
                <Icon className="w-4 h-4" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-xs font-semibold text-zinc-200 group-hover:text-blue-300 transition-colors">
                  {item.title}
                </p>
                <p className="text-[11px] text-zinc-400 line-clamp-2 mt-0.5">
                  {item.prompt}
                </p>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
};
