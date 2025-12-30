-- Create updates table for Warren VT community updates
CREATE TABLE IF NOT EXISTS public.updates (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  title TEXT NOT NULL,
  content TEXT NOT NULL,
  excerpt TEXT,
  category TEXT DEFAULT 'general',
  published_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Enable RLS for security
ALTER TABLE public.updates ENABLE ROW LEVEL SECURITY;

-- Allow public read access to updates (community data should be publicly viewable)
CREATE POLICY "updates_select_public"
  ON public.updates FOR SELECT
  USING (true);

-- Insert sample updates for Warren VT
INSERT INTO public.updates (title, content, excerpt, category) VALUES
(
  'New Property Transfer Data Available',
  'We''ve just updated our database with the latest property transfer records from the Vermont Property Transfer Tax Returns. This quarter shows a 15.2% increase in transfers compared to last year, with notable activity in the secondary home market.

Key highlights:
- 116 total transfers year-to-date
- Average property value increased to $525,000
- 45% of properties are classified as secondary homes
- Homestead exemption rate remains at 38%

The data reveals interesting trends in Warren''s housing market, particularly the continued conversion of primary residences to secondary homes. This aligns with broader patterns we''re seeing across the Mad River Valley.',
  'Latest property transfer data shows 15.2% increase in transfers with notable secondary home market activity.',
  'data-release'
),
(
  'Town Planning Board Meeting - Housing Policy Discussion',
  'The Warren Planning Board will hold a special meeting on February 15th to discuss proposed changes to the town''s housing policies. The meeting will focus on addressing the conversion of primary residences to short-term rentals and secondary homes.

Agenda items include:
- Review of current zoning regulations
- Discussion of potential short-term rental ordinance
- Analysis of housing affordability trends
- Public comment period

Community members are encouraged to attend and share their perspectives on these important housing issues affecting Warren.',
  'Special Planning Board meeting to discuss housing policies and short-term rental regulations.',
  'policy'
),
(
  'Mad River Valley Housing Study Released',
  'A comprehensive housing study for the Mad River Valley has been completed, providing detailed analysis of housing trends across Warren, Waitsfield, and Fayston. The study reveals significant challenges in maintaining affordable housing for year-round residents.

Key findings:
- 62% increase in median home prices over the past 5 years
- 28% of housing stock now used as short-term rentals
- Declining inventory of affordable rental units
- Growing gap between local wages and housing costs

The full report is available on the town website and will inform future housing policy decisions.',
  'New regional housing study reveals significant affordability challenges across the Mad River Valley.',
  'research'
);
