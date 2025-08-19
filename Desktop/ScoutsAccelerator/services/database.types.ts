
export type Json =
  | string
  | number
  | boolean
  | null
  | { [key: string]: Json | undefined }
  | Json[]

export type Database = {
  public: {
    Tables: {
      completed_requirements: {
        Row: {
          completed_at: string
          id: number
          rank_id: string
          requirement_id: string
          signed_off_by: string
          user_id: string
        }
        Insert: {
          completed_at?: string
          id?: number
          rank_id: string
          requirement_id: string
          signed_off_by: string
          user_id: string
        }
        Update: {
          completed_at?: string
          id?: number
          rank_id?: string
          requirement_id?: string
          signed_off_by?: string
          user_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "completed_requirements_rank_id_fkey"
            columns: ["rank_id"]
            isOneToOne: false
            referencedRelation: "ranks"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "completed_requirements_requirement_id_fkey"
            columns: ["requirement_id"]
            isOneToOne: false
            referencedRelation: "requirements"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "completed_requirements_signed_off_by_fkey"
            columns: ["signed_off_by"]
            isOneToOne: false
            referencedRelation: "profiles"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "completed_requirements_user_id_fkey"
            columns: ["user_id"]
            isOneToOne: false
            referencedRelation: "profiles"
            referencedColumns: ["id"]
          }
        ]
      }
      profiles: {
        Row: {
          current_rank_id: string | null
          id: string
          name: string | null
          role: "scout" | "scoutmaster" | "admin" | null
          troop_id: string | null
          updated_at: string | null
        }
        Insert: {
          current_rank_id?: string | null
          id: string
          name?: string | null
          role?: "scout" | "scoutmaster" | "admin" | null
          troop_id?: string | null
          updated_at?: string | null
        }
        Update: {
          current_rank_id?: string | null
          id?: string
          name?: string | null
          role?: "scout" | "scoutmaster" | "admin" | null
          troop_id?: string | null
          updated_at?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "profiles_current_rank_id_fkey"
            columns: ["current_rank_id"]
            isOneToOne: false
            referencedRelation: "ranks"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "profiles_troop_id_fkey"
            columns: ["troop_id"]
            isOneToOne: false
            referencedRelation: "troops"
            referencedColumns: ["id"]
          }
        ]
      }
      ranks: {
        Row: {
          id: string
          icon: string
          name: string
          sort_order: number
        }
        Insert: {
          id: string
          icon: string
          name: string
          sort_order: number
        }
        Update: {
          id?: string
          icon?: string
          name?: string
          sort_order?: number
        }
        Relationships: []
      }
      requirements: {
        Row: {
          description: string
          id: string
          lesson_content: Json | null
          rank_id: string
        }
        Insert: {
          description: string
          id: string
          lesson_content?: Json | null
          rank_id: string
        }
        Update: {
          description?: string
          id?: string
          lesson_content?: Json | null
          rank_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "requirements_rank_id_fkey"
            columns: ["rank_id"]
            isOneToOne: false
            referencedRelation: "ranks"
            referencedColumns: ["id"]
          }
        ]
      }
      sign_off_requests: {
        Row: {
          accepted_by: string | null
          created_at: string
          finalized_by: string | null
          id: string
          rank_id: string
          requirement_id: string
          scout_id: string
          status: "pending" | "accepted" | "approved" | "rejected"
          troop_id: string
        }
        Insert: {
          accepted_by?: string | null
          created_at?: string
          finalized_by?: string | null
          id?: string
          rank_id: string
          requirement_id: string
          scout_id: string
          status?: "pending" | "accepted" | "approved" | "rejected"
          troop_id: string
        }
        Update: {
          accepted_by?: string | null
          created_at?: string
          finalized_by?: string | null
          id?: string
          rank_id?: string
          requirement_id?: string
          scout_id?: string
          status?: "pending" | "accepted" | "approved" | "rejected"
          troop_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "sign_off_requests_accepted_by_fkey"
            columns: ["accepted_by"]
            isOneToOne: false
            referencedRelation: "profiles"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "sign_off_requests_finalized_by_fkey"
            columns: ["finalized_by"]
            isOneToOne: false
            referencedRelation: "profiles"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "sign_off_requests_rank_id_fkey"
            columns: ["rank_id"]
            isOneToOne: false
            referencedRelation: "ranks"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "sign_off_requests_requirement_id_fkey"
            columns: ["requirement_id"]
            isOneToOne: false
            referencedRelation: "requirements"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "sign_off_requests_scout_id_fkey"
            columns: ["scout_id"]
            isOneToOne: false
            referencedRelation: "profiles"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "sign_off_requests_troop_id_fkey"
            columns: ["troop_id"]
            isOneToOne: false
            referencedRelation: "troops"
            referencedColumns: ["id"]
          }
        ]
      }
      troops: {
        Row: {
          id: string
          join_code: string
          min_rank_for_sign_off_id: string | null
          name: string
          scoutmaster_id: string
        }
        Insert: {
          id?: string
          join_code: string
          min_rank_for_sign_off_id?: string | null
          name: string
          scoutmaster_id: string
        }
        Update: {
          id?: string
          join_code?: string
          min_rank_for_sign_off_id?: string | null
          name?: string
          scoutmaster_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "troops_min_rank_for_sign_off_id_fkey"
            columns: ["min_rank_for_sign_off_id"]
            isOneToOne: false
            referencedRelation: "ranks"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "troops_scoutmaster_id_fkey"
            columns: ["scoutmaster_id"]
            isOneToOne: false
            referencedRelation: "profiles"
            referencedColumns: ["id"]
          }
        ]
      }
    }
    Views: {
      [_ in never]: never
    }
    Functions: {
      [_ in never]: never
    }
    CompositeTypes: {
      [_ in never]: never
    }
  }
}
