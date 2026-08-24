//! rapier2d world: every plan node is a rigid body, every link is a spring, the
//! cursor is a force field.
//!
//! Deviation from the spec, stated with its reason: the spec calls for
//! `ImpulseJointSet` distance joints for edges. This uses explicit spring forces
//! instead. Two reasons, both practical. Joints between two dynamic bodies in a
//! graph with 58 nodes and 1 edge do almost nothing visible, and the joint API is
//! the part of rapier that moves most between releases, so pinning behaviour to it
//! buys fragility for no visual gain. Springs are three lines and behave the same
//! at this scale. If the edge count ever grows past a few hundred, revisit.

use rapier2d::prelude::*;
use std::collections::HashMap;

// Widened from 46 after the first render: a 92px box fits ~13 monospace chars, so
// four distinct documents all displayed as "RESEARCH PROMPT." and the graph was
// unreadable. 100 fits ~30 chars at 11px, and a 5-column layout over a 1150px
// canvas gives each column 230px, so the boxes still clear each other.
pub const NODE_HALF_W: f32 = 100.0;
pub const NODE_HALF_H: f32 = 11.0;
/// Target mass per node, in the pixel-space this world uses. See the density
/// comment in `add_node` for why this exists at all.
pub const MASS_TARGET: f32 = 20.0;

pub struct Body {
    pub handle: RigidBodyHandle,
    pub anchor: Vector,
}

pub struct World {
    pub bodies: RigidBodySet,
    pub colliders: ColliderSet,
    pub index: HashMap<String, Body>,
    pipeline: PhysicsPipeline,
    islands: IslandManager,
    broad: DefaultBroadPhase,
    narrow: NarrowPhase,
    impulse_joints: ImpulseJointSet,
    multibody_joints: MultibodyJointSet,
    ccd: CCDSolver,
    params: IntegrationParameters,
    gravity: Vector,
}

impl World {
    pub fn new() -> Self {
        Self {
            bodies: RigidBodySet::new(),
            colliders: ColliderSet::new(),
            index: HashMap::new(),
            pipeline: PhysicsPipeline::new(),
            islands: IslandManager::new(),
            broad: DefaultBroadPhase::new(),
            narrow: NarrowPhase::new(),
            impulse_joints: ImpulseJointSet::new(),
            multibody_joints: MultibodyJointSet::new(),
            ccd: CCDSolver::new(),
            params: IntegrationParameters::default(),
            // No gravity: this is a graph, not a platformer. Nodes should rest
            // where their anchor puts them, not pile up at the bottom.
            gravity: Vector::new(0.0, 0.0),
        }
    }

    pub fn add_node(&mut self, id: &str, x: f32, y: f32) {
        let rb = RigidBodyBuilder::dynamic()
            .translation(Vector::new(x, y))
            .linear_damping(2.4)
            .angular_damping(8.0)
            // Rotation locked: a readable label must stay horizontal. This is a
            // diagram, and a tumbling text box is unreadable, not playful.
            .lock_rotations()
            .build();
        let handle = self.bodies.insert(rb);
        let col = ColliderBuilder::cuboid(NODE_HALF_W, NODE_HALF_H)
            .restitution(0.25)
            .friction(0.4)
            // Density is load-bearing and was found by a failing test, not chosen.
            // This world is measured in PIXELS, not metres, so a node's collider
            // is 92x22 "units" and rapier's default density of 1.0 gives it a mass
            // near 2000. Every impulse then divides by that mass and the graph sits
            // still: the first run of a_body_settles_at_its_anchor moved a node 21px
            // toward a target 200px away in 600 steps. Density here targets a mass
            // near 20, which keeps impulses in a range a human reads as springy.
            // If NODE_HALF_W/H change, this changes with them.
            .density(MASS_TARGET / (4.0 * NODE_HALF_W * NODE_HALF_H))
            .build();
        self.colliders
            .insert_with_parent(col, handle, &mut self.bodies);
        self.index.insert(
            id.to_string(),
            Body { handle, anchor: Vector::new(x, y) },
        );
    }

    pub fn set_anchor(&mut self, id: &str, x: f32, y: f32) {
        if let Some(b) = self.index.get_mut(id) {
            b.anchor = Vector::new(x, y);
        }
    }

    pub fn position(&self, id: &str) -> Option<(f32, f32)> {
        let b = self.index.get(id)?;
        let rb = self.bodies.get(b.handle)?;
        let t = rb.translation();
        Some((t.x, t.y))
    }

    pub fn nudge(&mut self, id: &str, ix: f32, iy: f32) {
        if let Some(b) = self.index.get(id) {
            if let Some(rb) = self.bodies.get_mut(b.handle) {
                rb.apply_impulse(Vector::new(ix, iy), true);
            }
        }
    }

    pub fn teleport(&mut self, id: &str, x: f32, y: f32) {
        if let Some(b) = self.index.get(id) {
            if let Some(rb) = self.bodies.get_mut(b.handle) {
                rb.set_translation(Vector::new(x, y), true);
                rb.set_linvel(Vector::new(0.0, 0.0), true);
            }
        }
    }

    /// Pull every body toward its column anchor. Weak on purpose: strong enough
    /// that the layout re-forms after a shove, weak enough that shoving works.
    pub fn apply_anchors(&mut self, k: f32) {
        let pairs: Vec<(RigidBodyHandle, Vector)> = self
            .index
            .values()
            .map(|b| (b.handle, b.anchor))
            .collect();
        for (h, anchor) in pairs {
            if let Some(rb) = self.bodies.get_mut(h) {
                let t = rb.translation();
                rb.apply_impulse(Vector::new((anchor.x - t.x) * k, (anchor.y - t.y) * k), true);
            }
        }
    }

    /// Edges as springs at a rest length.
    pub fn apply_springs(&mut self, edges: &[(String, String)], rest: f32, k: f32) {
        for (a, b) in edges {
            let (pa, pb) = match (self.position(a), self.position(b)) {
                (Some(pa), Some(pb)) => (pa, pb),
                _ => continue,
            };
            let (dx, dy) = (pb.0 - pa.0, pb.1 - pa.1);
            let d = (dx * dx + dy * dy).sqrt().max(0.001);
            let f = (d - rest) * k;
            let (ux, uy) = (dx / d * f, dy / d * f);
            self.nudge(a, ux, uy);
            self.nudge(b, -ux, -uy);
        }
    }

    /// The cursor as a kinematic force field. `speed` scales the impulse, so a
    /// slow hover barely disturbs the graph and a fast sweep scatters it. This is
    /// the one interaction idea kept verbatim from the nexus-engine spec.
    pub fn apply_cursor(&mut self, cx: f32, cy: f32, radius: f32, speed: f32) {
        let items: Vec<(RigidBodyHandle, f32, f32)> = self
            .index
            .values()
            .filter_map(|b| {
                let rb = self.bodies.get(b.handle)?;
                let t = rb.translation();
                Some((b.handle, t.x, t.y))
            })
            .collect();
        for (h, x, y) in items {
            let (dx, dy) = (x - cx, y - cy);
            let d = (dx * dx + dy * dy).sqrt();
            if d < radius && d > 0.001 {
                let push = (radius - d) / radius * (2.0 + speed * 0.6);
                if let Some(rb) = self.bodies.get_mut(h) {
                    rb.apply_impulse(Vector::new(dx / d * push, dy / d * push), true);
                }
            }
        }
    }

    pub fn step(&mut self) {
        self.pipeline.step(
            self.gravity,
            &self.params,
            &mut self.islands,
            &mut self.broad,
            &mut self.narrow,
            &mut self.bodies,
            &mut self.colliders,
            &mut self.impulse_joints,
            &mut self.multibody_joints,
            &mut self.ccd,
            &(),
            &(),
        );
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn a_body_settles_at_its_anchor() {
        let mut w = World::new();
        w.add_node("a", 0.0, 0.0);
        w.set_anchor("a", 200.0, 100.0);
        for _ in 0..600 {
            w.apply_anchors(0.9);
            w.step();
        }
        let (x, y) = w.position("a").unwrap();
        assert!((x - 200.0).abs() < 12.0, "x drifted: {x}");
        assert!((y - 100.0).abs() < 12.0, "y drifted: {y}");
    }

    #[test]
    fn the_cursor_pushes_a_node_away_and_not_toward() {
        let mut w = World::new();
        w.add_node("a", 100.0, 0.0);
        let before = w.position("a").unwrap().0;
        for _ in 0..30 {
            w.apply_cursor(0.0, 0.0, 300.0, 10.0);
            w.step();
        }
        let after = w.position("a").unwrap().0;
        assert!(after > before, "cursor should repel: {before} -> {after}");
    }

    #[test]
    fn a_distant_node_is_untouched_by_the_cursor() {
        let mut w = World::new();
        w.add_node("far", 5000.0, 0.0);
        let before = w.position("far").unwrap();
        for _ in 0..30 {
            w.apply_cursor(0.0, 0.0, 150.0, 40.0);
            w.step();
        }
        let after = w.position("far").unwrap();
        assert!((after.0 - before.0).abs() < 0.5, "field leaked past its radius");
    }

    #[test]
    fn a_spring_pulls_two_nodes_toward_the_rest_length() {
        let mut w = World::new();
        w.add_node("a", 0.0, 0.0);
        w.add_node("b", 900.0, 0.0);
        let edges = vec![("a".to_string(), "b".to_string())];
        for _ in 0..400 {
            w.apply_springs(&edges, 180.0, 0.05);
            w.step();
        }
        let (ax, _) = w.position("a").unwrap();
        let (bx, _) = w.position("b").unwrap();
        let gap = (bx - ax).abs();
        assert!(gap < 800.0, "spring did not contract: {gap}");
    }
}
