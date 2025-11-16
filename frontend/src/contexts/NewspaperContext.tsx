import { createContext, useContext, useState, ReactNode } from "react";
import { startOfDay } from "date-fns";

interface NewspaperContextType {
  selectedDate: Date;
  setSelectedDate: (date: Date) => void;
}

const NewspaperContext = createContext<NewspaperContextType | undefined>(
  undefined
);

export function NewspaperProvider({ children }: { children: ReactNode }) {
  const [selectedDate, setSelectedDate] = useState(startOfDay(new Date()));

  return (
    <NewspaperContext.Provider value={{ selectedDate, setSelectedDate }}>
      {children}
    </NewspaperContext.Provider>
  );
}

export function useNewspaper() {
  const context = useContext(NewspaperContext);
  if (context === undefined) {
    throw new Error("useNewspaper must be used within a NewspaperProvider");
  }
  return context;
}
