import PageHeader from "../components/Layout/PageHeader";
import NewspaperView from "../components/Articles/NewspaperView";

export default function HomePage() {
  return (
    <div>
      <PageHeader
        title="Today"
        subtitle="Front page headlines and top stories • Curated by AI"
      />
      <NewspaperView showFallback={true} />
    </div>
  );
}
