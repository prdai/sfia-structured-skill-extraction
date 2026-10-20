import { Button } from "@/components/ui/button";

export const SAMPLES = [
  {
    label: "Senior backend engineer",
    text: "Senior backend engineer to design and build Python services, own API reliability, review code, mentor mid-level engineers, and lead incident response for a payments platform.",
  },
  {
    label: "Cloud solution architect",
    text: "Cloud solution architect responsible for enterprise migration strategy, reference architectures, stakeholder alignment, cost governance, and technical leadership across multi-cloud delivery teams.",
  },
  {
    label: "Data protection officer",
    text: "Data protection officer to own privacy compliance, run impact assessments, advise on data processing agreements, investigate incidents, and report to the board on regulatory risk.",
  },
  {
    label: "IT project manager",
    text: "IT project manager to plan and deliver a CRM rollout, manage scope, budget and vendors, coordinate business analysts and developers, and report progress to the steering committee.",
  },
];

export function Suggestions({ onSelect }: { onSelect: (text: string) => void }) {
  return (
    <div className="flex flex-wrap justify-center gap-2">
      {SAMPLES.map((sample) => (
        <Button
          key={sample.label}
          variant="outline"
          size="sm"
          onClick={() => onSelect(sample.text)}
        >
          {sample.label}
        </Button>
      ))}
    </div>
  );
}
