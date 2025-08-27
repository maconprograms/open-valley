-- Create members table for community directory
CREATE TABLE IF NOT EXISTS members (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  clerk_user_id TEXT UNIQUE NOT NULL,
  email TEXT NOT NULL,
  first_name TEXT NOT NULL,
  last_name TEXT NOT NULL,
  display_name TEXT,
  bio TEXT,
  hometown TEXT,
  partner_name TEXT,
  children JSONB DEFAULT '[]'::jsonb,
  pets JSONB DEFAULT '[]'::jsonb,
  phone TEXT,
  social_links JSONB DEFAULT '{}'::jsonb,
  profile_image_url TEXT,
  is_public BOOLEAN DEFAULT true,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create RLS policies
ALTER TABLE members ENABLE ROW LEVEL SECURITY;

-- Policy: Users can read all public profiles
CREATE POLICY "Public profiles are viewable by everyone" ON members
  FOR SELECT USING (is_public = true);

-- Policy: Users can insert their own profile
CREATE POLICY "Users can insert their own profile" ON members
  FOR INSERT WITH CHECK (clerk_user_id = auth.jwt() ->> 'sub');

-- Policy: Users can update their own profile
CREATE POLICY "Users can update own profile" ON members
  FOR UPDATE USING (clerk_user_id = auth.jwt() ->> 'sub');

-- Insert sample data
INSERT INTO members (clerk_user_id, email, first_name, last_name, display_name, bio, hometown, partner_name, children, pets, phone, social_links, profile_image_url) VALUES
('sample_user_1', 'sarah.johnson@email.com', 'Sarah', 'Johnson', 'Sarah J.', 'Long-time Warren resident, love hiking the local trails and volunteering at the school. Always happy to help newcomers get settled!', 'Warren, VT', 'Mike Johnson', '["Emma (12)", "Jake (9)"]'::jsonb, '["Buddy (Golden Retriever)", "Whiskers (Cat)"]'::jsonb, '(802) 555-0123', '{"instagram": "@sarahj_warren", "facebook": "sarah.johnson.warren"}'::jsonb, '/placeholder.svg?height=150&width=150'),
('sample_user_2', 'tom.miller@email.com', 'Tom', 'Miller', 'Tom M.', 'Moved here from Boston in 2019. Work remotely in tech, passionate about sustainable living and local food systems.', 'Originally Boston, MA', 'Lisa Miller', '["Sophie (6)"]'::jsonb, '["Charlie (Border Collie)"]'::jsonb, '(802) 555-0456', '{"linkedin": "tom-miller-warren", "twitter": "@tommiller_vt"}'::jsonb, '/placeholder.svg?height=150&width=150'),
('sample_user_3', 'jenny.adams@email.com', 'Jenny', 'Adams', 'Jenny A.', 'Third generation Warren resident! Love sharing stories about the valley''s history and organizing community events.', 'Warren, VT (born and raised)', NULL, '[]'::jsonb, '["Maple (Tabby Cat)", "Birch (Maine Coon)"]'::jsonb, '(802) 555-0789', '{"facebook": "jenny.adams.warren"}'::jsonb, '/placeholder.svg?height=150&width=150');
