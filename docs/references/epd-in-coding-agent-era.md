# EPD in the Era of Coding Agents

> **作者**: Harrison Chase (hwchase17)
> **来源**: [Twitter/X](https://x.com/hwchase17/status/2031051115169808685)

---

EPD (Engineering, Product, and Design) at software company is about creating good software. Separate roles exist, but the end goal is functional software that solves a business problem that users can use. At the end of the day, this is just code.

It is important to recognize that the output of what EPD as a function builds is just code because… **coding agents have suddenly made code very easy to write.** So how does this change the role of EPD?

## The Changing Process

- **PRDs are dead**
- **The bottleneck shifts from implementation to review**
- **Long live PRDs**

## Impact on Roles

- **Generalists are more valuable than ever**
- **Coding agents are a requirement**
- **Good PMs are great, bad PMs are terrible**
- **Everyone needs product sense**
- **The bar for specialization is higher**
- **You're either a builder or a reviewer**
- **Everyone thinks their role is most advantaged by coding agents - and they are right**

---

## The Traditional PRD Process (Pre-Claude Era)

PRDs (Product Requirement Documents) were the focal point of building software in the pre-Claude era. The EPD process was largely:

1. Someone (usually product) has an idea
2. Product writes a PRD
3. Design takes PRD and creates a mock
4. Engineering turns mock into code

This wasn't a hard and fast rule (at startups these steps blended together, the best builders were able to do multiple of these together) but it was the textbook way to build things.

This was required because building the software (and building the mock) required a significant amount of time and effort. So disciplines were created to specialize in those efforts. As people became more specialized, there then became a need to communicate across those disciplines. The PRD was the basis of that, which kickstarted everything. It would then waterfall to design, who would turn pretty words into a pretty UI and smooth UX. Engineering would then make that real.

## Coding Agents Change Everything

Coding agents change all of that. **Coding agents can take an idea and create functional software.** When I (and others) say "PRDs are dead" what we really mean is this traditional way of building software, starting with the writing of a PRD, is dead.

Anyone can write code now, which means anyone can build things. That does not mean the things that are built are well architected, or solve the right problems, or easy to use. Engineering, Product, and Design should be the reviewers and arbitrators of these areas.

The issue is the code generated isn't always "great". The role of EPD becomes reviewing and making sure it is "great". "Great" can mean several things:

- **Well architected from an engineering systems perspective**: is it written in a scalable, performant, robust way?
- **Well thought out from a product perspective**: does this solve the user pain point?
- **Well designed**: are the interfaces easy and intuitive to use?

Since the cost of creating some initial version of the code is so cheap, we see that a lot more prototypes are created. Those prototypes then serve as a focal point, with Product, Engineering, and Design reviewing them.

## The New Bottleneck: Review

The issue is - it's so easy to generate code. Previously, it took a while to create the code - so as a reviewer there were only so many projects coming across your desk for review at any given point. Now though - anyone can write code. That means the number of projects going on is increasing. **We've seen the bottleneck (in all three functions) be review** - taking the prototypes and making sure they are "good".

## Long Live PRDs

The pre-Claude era of building software (starting with a PRD) is gone. But documents describing product requirements are still essential.

Let's assume someone has an idea and quickly builds a prototype. How does this get into production? It needs to be reviewed by other members of EPD. As part of this process, a written document always helps and is often essential. When others are reviewing, how are they to know if part of the code is there by accident or on purpose? Depends on the intent. Some communication of this intent is needed.

I think the traditional PRD process (PRD → mock → code) is dead. But text that describes product requirements is very much alive. This associated document should be a required companion to the prototype before being handed off for review.

The most standard format would be a document, but there are some interesting ideas around sharing the prompts used to create this feature as a way to communicate that. **What if PRDs of the future are just structured, versioned prompts?**

---

## Generalists Are More Valuable Than Ever

By generalists I mean people with a good sense of all three of product, engineering and design. These people were always valuable and impactful - but with coding agents they are even more so. Why?

**Communication is the hardest part of everything.** It slows things down. One person who can do all of product, design, and engineering will move faster than a team of three because of the communication overhead.

Previously, when implementation was the blocker, this generalist still had to communicate with others to get work done. Now they can just communicate with agents. This means they can be far more impactful by just themselves than ever before.

## Coding Agents Are a Requirement

With coding agents making implementation cheap, using them is a requirement. People who can adopt coding agents will be able to do more by themselves:

- **PMs** who adopt coding agents can validate ideas by building prototypes directly, without writing a spec and waiting
- **Designers** who adopt coding agents can iterate in code, not just in Figma
- **Engineers** who adopt coding agents can shift their time from implementation to system thinking

Adopting coding agents is a requirement because it is not hard to do so, and if you don't do so you will be replaced by someone who does.

## Good PMs Are Great, Bad PMs Are Terrible

Good product thinking is more valuable than ever - you can build things that are useful. Bad product thinking is more wasteful than ever. If someone has a bad product idea, they can show up with a prototype - but that prototype will be of a feature that is useless, or poorly conceived. These prototypes now require more reviews - from engineering, product and design. This sucks up time and resources. There is also more inertia to get these prototypes into production ("It already exists! Let's just merge it!"). This risks creating a worse or bloated product.

## Everyone Needs Product Sense

In a world where execution is cheap, system thinking becomes the differentiator. You should focus on being really good at systems thinking and have a clear mental model of your particular domain:

- **Engineering**: really good mental model of how to architect services and APIs and databases
- **Product**: really good mental model of what users actually need, not what they say they want
- **Design**: really good mental model of why something looks and feels right to use

System thinking has always been important - so what has changed? The cost of implementation went way down. This means that it is easier than ever to implement something - but that doesn't mean it's great. Being a good system thinker allows you make sure you are building the right things upfront. It also lets you review others work after the fact. Both mean that the importance of being a good system thinker has grown.

Coding agents still need someone to prompt them. Someone to tell them what to do. If you tell them to build the wrong thing - you are creating more slop for others to review. **Knowing what to tell the agent to build ("product sense") is a requirement**, or you will be a drag on the org. This is true across engineering, design, and (obviously) product.

A big part of EPD is now reviewing prototypes. Reviewing is easier if you have product sense, even for reviewing design/engineering. If you don't have product sense, you need a super detailed product document along side the prototype. If you do have product sense you understand the intent of the feature with a minimal spec, speeding up communication, review, and delivery.

You need to know how to use coding agents. You need product sense. **All the roles are blending together.**

## The Bar for Specialization is Higher

There's always been overlap in roles. Design and product have long been linked - at certain companies like Apple and AirBnb, designers serve as product managers. "Design engineer" as a role has been picking up steam at companies like Vercel.

This doesn't mean there is no room for specialization. A very senior engineer who just thinks about the system architecture is still valuable. As is a PM who hasn't picked up vibe coding but does have a super clear mental model of the customers problems and what to build. Same with a designer who can understand and mock user journeys and interactions, even if still in Figma.

But **the bar for specialization is much higher**. You have to be not only fantastic at your domain, but also incredibly fast at review and an incredible communicator. And there probably aren't that many of these roles at any given company.

---

## Two Emerging Archetypes: Builder vs Reviewer

We see two different types of roles emerging in EPD.

### The Builder

This archetype has good product thinking, they are capable of using coding agents, and have baseline design intuition. With guardrails around them (test suite, component library) they can take small features from idea to production, and prototype functional versions of larger ones.

### The Reviewer

For large and complicated features, detailed EPD review is required. The bar for this is high - you have to be a fantastic systems thinker in your domain. You also have to work at a fast pace - there is a lot to review.

---

## Career Implications

- **If you are an engineer right now** - you should either aim to get fantastic at system design and comfortable reviewing architectures and aim to be a reviewer… or try to grow your product/design skills and become a builder.

- **If you are in product or design** - you either have to have a fantastic mental model for product/design and largely review, or jump into coding agents and improving your coding chops.

What's interesting is that roles are kind of collapsing, as shown by all of EPD being somewhere on the above chart. Roles can start to blend together - engineers have more time, can think more on product and design. Product and design can create code.

---

## The Unicorn Archetype

There was a [post](https://x.com/biancawagner/status/2029960676299030528) about the type of people most advantaged by coding agents:

> someone with an intuitive grasp of the product as it exists, where it's soft, where it sings, & how to iterate it toward something even sharper.
>
> the rarest version of this person sits at the intersection of culture & deep technology. someone genuinely bilingual. they know what's technically possible & they know which cultural currents are real vs. ephemeral. that combo is what separates products that feel inevitable from products that feel assembled.

The post was a great encapsulation of this new world, and it went semi-viral. Part of the reason it went viral was everyone reading it thought it was about them or their role. I saw product people quoting it, designers, design engineers, founders… everyone thought it applied to them and their role.

**And they were all probably right!** I think the great and exciting thing about this new world is that backgrounds matter less. I genuinely believe this archetype of person could come from product, design, or engineering. That doesn't mean everyone will be this person - it's much easier said than done. There are very few true unicorns out there.

---

**It's an exciting time to be building :)**
