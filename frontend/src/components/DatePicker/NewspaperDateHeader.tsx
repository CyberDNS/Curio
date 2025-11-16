import { useState } from "react";
import { format, parseISO, subDays, startOfDay, isSameDay } from "date-fns";

interface NewspaperDateHeaderProps {
  currentDate: Date;
  availableDates: string[];
  onDateChange: (date: Date) => void;
}

export default function NewspaperDateHeader({
  currentDate,
  availableDates,
  onDateChange,
}: NewspaperDateHeaderProps) {
  const [isOpen, setIsOpen] = useState(false);

  // Convert available dates to Date objects for comparison
  const availableDateObjects = availableDates.map((d) => startOfDay(parseISO(d)));

  // Generate last 7 days
  const dates = Array.from({ length: 7 }, (_, i) => {
    return startOfDay(subDays(new Date(), i));
  });

  const handleDateClick = (date: Date) => {
    onDateChange(date);
    setIsOpen(false);
  };

  const isDateAvailable = (date: Date) => {
    return availableDateObjects.some((d) => isSameDay(d, date));
  };

  const isToday = isSameDay(currentDate, new Date());

  return (
    <div className="relative inline-block">
      {/* Current Date Display - Newspaper Style */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="px-2 py-0.5 hover:bg-newspaper-100 transition-colors font-serif text-newspaper-700 cursor-pointer border-b border-dashed border-newspaper-400"
      >
        <span className="text-xs md:text-sm">
          {isToday ? (
            <>
              <span className="font-bold">TODAY</span> • {format(currentDate, "MMMM d, yyyy")}
            </>
          ) : (
            format(currentDate, "EEEE, MMMM d, yyyy")
          )}
        </span>
      </button>

      {/* Calendar Dropdown - Newspaper themed */}
      {isOpen && (
        <>
          {/* Backdrop */}
          <div
            className="fixed inset-0 z-40"
            onClick={() => setIsOpen(false)}
          />

          {/* Calendar Panel */}
          <div className="absolute top-full left-0 mt-2 bg-white border-4 border-newspaper-900 shadow-2xl z-50 min-w-[320px]">
            {/* Header */}
            <div className="bg-newspaper-900 text-white text-center py-2 px-4">
              <div className="font-serif font-bold text-sm tracking-wider">
                EDITION ARCHIVE
              </div>
              <div className="text-xs opacity-90 mt-0.5">Last 7 Days</div>
            </div>

            {/* Editions List */}
            <div className="divide-y divide-newspaper-300 max-h-[400px] overflow-y-auto">
              {dates.map((date) => {
                const isAvailable = isDateAvailable(date);
                const isSelected = isSameDay(date, currentDate);
                const isTodayDate = isSameDay(date, new Date());

                return (
                  <button
                    key={date.toISOString()}
                    onClick={() => isAvailable && handleDateClick(date)}
                    disabled={!isAvailable}
                    className={`
                      w-full text-left px-4 py-3 transition-colors
                      ${isSelected
                        ? "bg-newspaper-900 text-white"
                        : isAvailable
                        ? "hover:bg-newspaper-100 text-newspaper-900 bg-white"
                        : "text-newspaper-400 cursor-not-allowed bg-newspaper-50"
                      }
                    `}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex-1">
                        <div className={`font-serif text-sm ${isSelected ? "font-bold" : "font-medium"}`}>
                          {format(date, "EEEE")}
                        </div>
                        <div className={`text-xs ${isSelected ? "opacity-90" : "text-newspaper-600"}`}>
                          {format(date, "MMMM d, yyyy")}
                        </div>
                        {isTodayDate && (
                          <div className={`text-xs mt-0.5 ${isSelected ? "text-white opacity-75" : "text-blue-600 font-semibold"}`}>
                            TODAY'S EDITION
                          </div>
                        )}
                      </div>
                      {!isAvailable && (
                        <div className="text-xs italic text-newspaper-500">
                          Not Published
                        </div>
                      )}
                      {isSelected && (
                        <div className="text-xs font-bold">
                          READING
                        </div>
                      )}
                    </div>
                  </button>
                );
              })}
            </div>

            {/* Footer */}
            <div className="bg-newspaper-100 text-center py-2 border-t-2 border-newspaper-300">
              <div className="text-xs text-newspaper-600 font-serif italic">
                Newspapers are generated hourly
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
